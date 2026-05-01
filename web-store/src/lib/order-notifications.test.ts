import { describe, expect, it, vi } from "vitest";
import { sendOrderNotificationSafely } from "@/lib/order-notifications";

describe("sendOrderNotificationSafely", () => {
  it("does not fail checkout when Telegram notification fails", async () => {
    const result = await sendOrderNotificationSafely(
      {
        orderNumber: "ORD-1",
        customerName: "Иван",
        phone: "+79780000000",
        email: null,
        comment: null,
        quote: {
          items: [],
          total: 0,
        },
      },
      vi.fn().mockRejectedValue(new Error("telegram unavailable")),
    );

    expect(result).toEqual({ skipped: true, error: "telegram unavailable" });
  });
});
