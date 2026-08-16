import requests
import re
import json


MOCK_SERVER_URL = "http://127.0.0.1:5000"


def get_customer():
    try:
        response = requests.get(
            f"{MOCK_SERVER_URL}/customer",
            timeout=5
        )
        response.raise_for_status()
        return response.json()

    except requests.RequestException:
        return None


def save_call_result(customer_id, outcome, promised_date):
    payload = {
        "message": {
            "type": "tool-calls",
            "toolCalls": [
                {
                    "id": "voicebot-disposition-001",
                    "function": {
                        "name": "mark_disposition",
                        "arguments": {
                            "account_id": "ACC-88392",
                            "status": outcome,
                            "notes": (
                                f"Customer promised to pay on {promised_date}."
                                if promised_date
                                else "Call outcome recorded."
                            )
                        }
                    }
                }
            ]
        }
    }

    try:
        response = requests.post(
            f"{MOCK_SERVER_URL}/webhook",
            json=payload,
            timeout=5
        )

        response.raise_for_status()
        data = response.json()

        if data.get("results"):
            result = json.loads(data["results"][0]["result"])

            if result.get("success"):
                return {
                    "result_id": result.get("result_id"),
                    "success": True
                }

        return None

    except requests.RequestException as error:
        print(f"Bot: Unable to save call result: {error}")
        return None


def analyze_response(customer_response):
    response = customer_response.lower().strip()

    # Dispute outstanding amount
    if any(phrase in response for phrase in [
        "wrong amount",
        "amount is wrong",
        "incorrect amount",
        "outstanding amount is wrong",
        "i don't agree",
        "i disagree",
        "dispute",
        "this is not my amount"
    ]):
        return (
            "Bot: I understand that you dispute the outstanding amount. "
            "I'll connect you with a human agent to review this.",
            "ESCALATE",
            "Customer disputes the outstanding amount."
        )

    # Request human agent
    if any(phrase in response for phrase in [
        "speak to an agent",
        "talk to an agent",
        "human agent",
        "customer care",
        "representative",
        "connect me to someone"
    ]):
        return (
            "Bot: Certainly. I'll connect you with a human agent.",
            "ESCALATE",
            "Customer requested a human agent."
        )

    # Already paid
    if any(phrase in response for phrase in [
        "already paid",
        "paid already",
        "payment done",
        "i have paid"
    ]):
        return (
            "Bot: I understand. I'll note that you have already made the payment.",
            "ALREADY_PAID",
            None
        )

    # Wrong number
    if any(phrase in response for phrase in [
        "wrong number",
        "wrong person",
        "not rahul",
        "not me"
    ]):
        return (
            "Bot: I apologize for the inconvenience. "
            "I'll note that this is not the correct contact.",
            "WRONG_NUMBER",
            None
        )

    # Payment difficulty
    if any(phrase in response for phrase in [
        "can't pay",
        "cannot pay",
        "unable to pay",
        "no money",
        "don't have money",
        "not able to pay"
    ]):
        return (
            "Bot: I understand that you're facing difficulty with the payment. "
            "Could you please tell me when you expect to make the payment?",
            "PAYMENT_DIFFICULTY",
            None
        )

    # Payment link
    if any(phrase in response for phrase in [
        "payment link",
        "send me the link",
        "link to pay",
        "send the link"
    ]):
        return (
            "Bot: Certainly. I'll arrange for a payment link to be sent "
            "to your registered mobile number.",
            "SEND_PAYMENT_LINK",
            None
        )

    # Specific payment date
    date_match = re.search(
        r"\b(\d{1,2}\s+(?:january|february|march|april|may|june|july|august|"
        r"september|october|november|december)\s+\d{4})\b",
        response
    )

    if date_match:
        promised_date = date_match.group(1)

        return (
            f"Bot: Thank you. I've noted your commitment to make "
            f"the payment on {promised_date}.",
            "PROMISE_TO_PAY",
            promised_date
        )

    # Tomorrow
    if "tomorrow" in response:
        return (
            "Bot: Thank you. I've noted your commitment to make "
            "the payment tomorrow.",
            "PROMISE_TO_PAY",
            "tomorrow"
        )

    # Today
    if "today" in response:
        return (
            "Bot: Thank you. I've noted your commitment to make "
            "the payment today.",
            "PROMISE_TO_PAY",
            "today"
        )

    # Next week
    if "week" in response:
        return (
            "Bot: Thank you. I've noted your expected payment "
            "for next week.",
            "PROMISE_TO_PAY",
            "next week"
        )

    return (
        "Bot: Thank you for the information. "
        "I'll note your response for further processing.",
        "UNCLASSIFIED",
        None
    )


def main():
    print("Kapture Collections Voicebot")
    print("----------------------------")

    customer = get_customer()

    if not customer:
        print("Bot: I'm unable to access the customer account right now.")
        return

    print(
        f"\nBot: Hello {customer['name']}, "
        "this is a call regarding your loan account."
    )

    print(
        f"Bot: Your outstanding amount is "
        f"₹{customer['overdue_amount']}."
    )

    print(
        f"Bot: You are {customer['days_past_due']} days past due."
    )

    print("Bot: When would you be able to make the payment?")

    customer_response = input("Customer: ")

    bot_response, outcome, promised_date = analyze_response(
        customer_response
    )

    print(bot_response)

    # Escalation flow
    if outcome == "ESCALATE":

        escalation_payload = {
            "message": {
                "type": "tool-calls",
                "toolCalls": [
                    {
                        "id": "voicebot-escalation-001",
                        "function": {
                            "name": "escalate_to_agent",
                            "arguments": {
                                "reason": promised_date
                            }
                        }
                    }
                ]
            }
        }

        try:
            response = requests.post(
                f"{MOCK_SERVER_URL}/webhook",
                json=escalation_payload,
                timeout=5
            )

            response.raise_for_status()
            escalation_result = response.json()

            print("Bot: Escalation request sent successfully.")
            print(f"Escalation Result: {escalation_result}")

        except requests.RequestException as error:
            print(f"Bot: Unable to escalate to agent: {error}")

    # Payment difficulty follow-up
    if outcome == "PAYMENT_DIFFICULTY":

        payment_date = input("Customer: ")

        if payment_date.strip():

            date_match = re.search(
                r"\b(\d{1,2}\s+(?:january|february|march|april|may|june|july|august|"
                r"september|october|november|december)\s+\d{4})\b",
                payment_date.lower()
            )

            if date_match:
                promised_date = date_match.group(1)
            else:
                promised_date = payment_date

            outcome = "PROMISE_TO_PAY"

            print(
                f"Bot: Thank you. I've noted your expected "
                f"payment date as {promised_date}."
            )

    # Save final call result
    result = save_call_result(
        customer["customer_id"],
        outcome,
        promised_date
    )

    print("\n--- Call Result ---")
    print(f"Customer ID: {customer['customer_id']}")
    print(f"Outcome: {outcome}")
    print(f"Promised Date: {promised_date}")

    if result:
        print("Call result saved successfully.")
        print(f"Result ID: {result['result_id']}")


if __name__ == "__main__":
    main()