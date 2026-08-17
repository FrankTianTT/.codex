# 行为测试示例

## 推荐

```typescript
test("有效购物车可以完成结算", async () => {
  const cart = createCart();
  cart.add(product);

  const result = await checkout(cart, paymentMethod);

  expect(result.status).toBe("confirmed");
  expect(result.orderId).toBeDefined();
});
```

这个测试通过公开入口描述一个完整行为。两个断言共同证明同一个结算结果，不必机械拆成两个测试。

## 避免

```typescript
test("checkout 调用 paymentService.process 一次", async () => {
  const process = jest.spyOn(paymentService, "process");
  await checkout(cart, paymentMethod);
  expect(process).toHaveBeenCalledTimes(1);
});
```

如果调用次数不是外部契约，这个测试会把内部组织方式锁死。重构没有改变结算行为时，它也可能无意义地失败。

## 判断问题

- 测试名是否描述调用者能观察到的能力？
- 改写内部实现但保持行为不变时，测试是否仍应通过？
- 失败信息能否指出哪个行为被破坏？
- 当前层级是否是验证该风险最便宜、最稳定的位置？
