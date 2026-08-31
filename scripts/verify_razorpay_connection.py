from app.payments import create_order, get_order

# Full create -> pay -> refund needs a real payment_id, which only exists
# after an actual payment is made (Razorpay requires this go through their
# secure checkout, not a script). See scripts/create_test_payment_link.py
# for that step. This script only verifies the API connection itself.


def main():
    print("Creating a ₹1000.00 test order...")
    order_id = create_order(amount=100000)
    print(f"Created: {order_id}")

    order = get_order(order_id)
    print(f"Fetched: {order}")


if __name__ == "__main__":
    main()
