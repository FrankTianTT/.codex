// ============================================================================
// Local OCR — Apple Vision CLI Wrapper (Enhanced)
//
// Version: 2.0
// Source: local-ocr Skill
//
// 本工具在调用 Apple Vision 前显式执行一条 Core Image 预处理管线，便于控制
// 扫描件增强、对比度、锐化和缩放策略。
//
// 预处理管线:
//   Raw Image → CIDocumentEnhancer → CIColorControls → Scale → Vision OCR
//
// 硬件加速路径 (M5):
//   Core Image 预处理 → GPU (Metal)
//   Vision 文字识别   → ANE (Neural Engine)
//   两条管线异步流水，互不阻塞
//
// 使用:
//   ocr_vision <image-path> [lang: en|zh|ja|cjk|auto]
//   ocr_vision <image-path> [lang] --raw        # 跳过预处理
//   ocr_vision <image-path> [lang] --enhance    # 仅文档增强
//
// 编译:
//   scripts/build.sh
//
// ============================================================================

import Vision
import Foundation
import CoreImage
import ImageIO

// ── 命令行解析 ────────────────────────────────────────────────────────────

let args = CommandLine.arguments

guard args.count > 1 else {
    fputs("""
    使用: ocr_vision <image-path> [lang: en|zh|ja|cjk|auto] [options]

    Options:
      --raw        跳过预处理，直接 OCR（用于已是高质量图片的情况）
      --enhance    仅文档增强模式（CIDocumentEnhancer + 轻微对比度）
      --full       完整预处理管线: 文档增强 + 对比度 + 锐化（默认）

    Lang:
      en   英文优先
      zh   中文优先
      ja   日文优先
      cjk  中日英同时识别（用于语言检测场景）
      auto 自动检测（使用系统首选语言，不推荐用于 CJK）

    """, stderr)
    exit(1)
}

let imagePath = args[1]

var langMode = "en"
var preprocessMode = "full"

for i in 2..<args.count {
    let arg = args[i]
    switch arg {
    case "--raw":    preprocessMode = "raw"
    case "--enhance": preprocessMode = "enhance"
    case "--full":   preprocessMode = "full"
    case "en", "zh", "ja", "auto", "cjk": langMode = arg
    default: fputs("[warning] 未知参数已忽略: \(arg)\n", stderr)
    }
}

// ── 预处理管线 ────────────────────────────────────────────────────────────

/// 文档增强 — Apple 专门为扫描文档设计的滤镜
/// 这是 Shortcuts OCR 的核心预处理步骤
func applyDocumentEnhancer(_ image: CIImage) -> CIImage {
    guard let filter = CIFilter(name: "CIDocumentEnhancer") else {
        fputs("  [preprocess] CIDocumentEnhancer 不可用，跳过\n", stderr)
        return image
    }
    filter.setValue(image, forKey: kCIInputImageKey)
    filter.setValue(3.0, forKey: kCIInputAmountKey) // 1-10，3 是温和增强
    return filter.outputImage ?? image
}

/// 对比度增强 — 让文字更清晰，背景更干净
func applyContrastBoost(_ image: CIImage) -> CIImage {
    guard let filter = CIFilter(name: "CIColorControls") else { return image }
    filter.setValue(image, forKey: kCIInputImageKey)
    filter.setValue(1.15, forKey: kCIInputContrastKey)   // 1.15x 对比度（不激进）
    filter.setValue(0.0,  forKey: kCIInputBrightnessKey) // 不动亮度
    filter.setValue(1.0,  forKey: kCIInputSaturationKey) // 不动饱和度
    return filter.outputImage ?? image
}

/// 轻微锐化 — 增强文字边缘
func applySharpen(_ image: CIImage) -> CIImage {
    guard let filter = CIFilter(name: "CISharpenLuminance") else { return image }
    filter.setValue(image, forKey: kCIInputImageKey)
    filter.setValue(0.3, forKey: kCIInputSharpnessKey) // 0.3 = 很轻微的锐化
    return filter.outputImage ?? image
}

/// 缩放到合理尺寸 — 太大浪费算力，太小丢失细节
func scaleIfNeeded(_ image: CIImage, maxDimension: CGFloat = 2400) -> CIImage {
    let extent = image.extent
    let maxSide = max(extent.width, extent.height)
    guard maxSide > maxDimension else { return image }

    let scale = maxDimension / maxSide
    // 用 CILanczosScaleTransform 做高质量缩放
    guard let filter = CIFilter(name: "CILanczosScaleTransform") else { return image }
    filter.setValue(image, forKey: kCIInputImageKey)
    filter.setValue(scale, forKey: kCIInputScaleKey)
    filter.setValue(1.0,  forKey: kCIInputAspectRatioKey)
    return filter.outputImage ?? image
}

/// 执行完整的预处理管线
func preprocess(_ image: CIImage, mode: String) -> CIImage {
    var result = image

    // Step 1: 缩放到合理尺寸
    result = scaleIfNeeded(result)

    switch mode {
    case "raw":
        // 什么预处理都不做
        break

    case "enhance":
        // 仅文档增强（最保守，适合大多数场景）
        result = applyDocumentEnhancer(result)
        result = applyContrastBoost(result)

    case "full":
        // 完整管线
        result = applyDocumentEnhancer(result)
        result = applyContrastBoost(result)
        result = applySharpen(result)

    default:
        break
    }

    return result
}

// ── 图像加载 ──────────────────────────────────────────────────────────────

func loadImage(_ path: String) -> CIImage? {
    let url = URL(fileURLWithPath: path)

    // 先尝试 Core Image 直接加载（最高保真路径）
    if let ciImage = CIImage(contentsOf: url) {
        return ciImage
    }

    // 兜底：通过 ImageIO 加载
    guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
          let cgImage = CGImageSourceCreateImageAtIndex(source, 0, nil)
    else {
        return nil
    }
    return CIImage(cgImage: cgImage)
}

// ── OCR 请求配置 ──────────────────────────────────────────────────────────

func createTextRequest(lang: String) -> VNRecognizeTextRequest {
    let request = VNRecognizeTextRequest()

    // 语言配置
    switch lang {
    case "zh":
        // 简体中文优先，繁体中文其次，英文兜底
        request.recognitionLanguages = ["zh-Hans", "zh-Hant", "en-US"]
    case "en":
        request.recognitionLanguages = ["en-US", "zh-Hans"]
    case "ja":
        // 日文优先
        request.recognitionLanguages = ["ja-JP", "en-US"]
    case "cjk":
        // 中日英同时识别 — 用于语言检测场景
        request.recognitionLanguages = ["zh-Hans", "zh-Hant", "ja-JP", "en-US"]
    case "auto":
        // 不指定语言偏好，Vision 自行检测
        request.recognitionLanguages = []
    default:
        request.recognitionLanguages = ["en-US", "zh-Hans"]
    }

    request.recognitionLevel = .accurate        // 完整神经网络模型
    request.usesLanguageCorrection = true       // 语言模型纠错（如 "Icould" → "I could"）
    request.minimumTextHeight = 0.003           // 过滤小于画面高度 0.3% 的文字（噪音/水印）
    request.revision = VNRecognizeTextRequestRevision3  // 固定接口 revision；底层系统模型仍可能变化

    return request
}

// ── 主流程 ────────────────────────────────────────────────────────────────

guard let rawImage = loadImage(imagePath) else {
    fputs("ERROR: 无法加载图片: \(imagePath)\n", stderr)
    exit(1)
}

let originalSize = rawImage.extent
fputs("[preprocess] 模式: \(preprocessMode)\n", stderr)
fputs("[preprocess] 原始尺寸: \(Int(originalSize.width))x\(Int(originalSize.height))\n", stderr)

// 预处理
let processedImage = preprocess(rawImage, mode: preprocessMode)
let processedSize = processedImage.extent

if preprocessMode != "raw" {
    fputs("[preprocess] 处理后尺寸: \(Int(processedSize.width))x\(Int(processedSize.height))\n", stderr)
}

// OCR 识别
let request = createTextRequest(lang: langMode)
let handler = VNImageRequestHandler(ciImage: processedImage, options: [:])

do {
    try handler.perform([request])

    guard let results = request.results else {
        print("NO TEXT FOUND")
        exit(0)
    }

    var outputCount = 0
    for observation in results {
        guard let topCandidate = observation.topCandidates(1).first else { continue }

        let confidence = topCandidate.confidence
        // 置信度 0.2 — 过滤明显噪声，保留低对比度但真实存在的文字
        if confidence > 0.2 {
            print(topCandidate.string)
            outputCount += 1
            fputs("[debug] \"\(topCandidate.string.prefix(60))...\" conf=\(String(format: "%.2f", confidence))\n", stderr)
        }
    }

    fputs("[result] 识别到 \(outputCount) 行文字\n", stderr)

    if outputCount == 0 {
        print("NO TEXT FOUND")
    }

} catch {
    fputs("ERROR: Vision 请求失败: \(error)\n", stderr)
    exit(1)
}
