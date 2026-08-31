from app.payments import create_payment_link

# Razorpay requires an actual payment to go through their checkout (for
# security/compliance reasons, there's no way to script this part). Run
# this once, open the printed link, pay it with a Razorpay test card,
# then find the resulting payment_id in the Dashboard under Payments.


def main():
    url = create_payment_link(amount=100000, description="Milestone 8 test payment")
    print(f"Open this link and pay it with a Razorpay test card:\n{url}")


if __name__ == "__main__":
    main()
