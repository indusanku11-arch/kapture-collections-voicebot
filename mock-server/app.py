from flask import Flask, jsonify, request
import sqlite3
from datetime import datetime
import random


app = Flask(__name__)

DATABASE = "kapture.db"


def init_database():
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS call_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL,
            outcome TEXT NOT NULL,
            promised_date TEXT,
            notes TEXT
        )
    """)

    connection.commit()
    connection.close()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "kapture-collections-voicebot-mock"
    })


@app.route("/customer", methods=["GET"])
def customer():
    return jsonify({
        "customer_id": "CUST001",
        "account_id": "ACC-88392",
        "name": "Rahul Sharma",
        "loan_type": "Personal Loan",
        "overdue_amount": 8499,
        "days_past_due": 12
    })


def verify_customer(args):
    verification_code = str(args.get("verification_code", ""))

    if verification_code in ["1234", "1995"]:
        return {
            "verified": True,
            "message": "Identity verified successfully."
        }

    return {
        "verified": False,
        "message": "Verification failed. Incorrect code."
    }


def log_promise_to_pay(args):
    account_id = args.get("account_id")
    ptp_date = args.get("ptp_date")
    amount = args.get("amount")

    ptp_id = f"PTP-{random.randint(1000, 9999)}"

    return {
        "success": True,
        "ptp_id": ptp_id,
        "account_id": account_id,
        "confirmed_date": ptp_date,
        "amount": amount
    }


def send_payment_link(args):
    account_id = args.get("account_id")
    channel = args.get("channel")

    return {
        "success": True,
        "account_id": account_id,
        "message": (
            f"Payment link sent successfully via {channel} "
            "to the registered mobile number."
        )
    }


def escalate_to_agent(args):
    reason = args.get("reason")

    return {
        "success": True,
        "escalated": True,
        "reason": reason,
        "message": "The customer has been routed to a human agent."
    }


def mark_disposition(args):
    account_id = args.get("account_id")
    status = args.get("status")
    notes = args.get("notes", "")

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO call_results
        (customer_id, outcome, promised_date, notes)
        VALUES (?, ?, ?, ?)
    """, (
        account_id,
        status,
        None,
        notes
    ))

    connection.commit()

    result_id = cursor.lastrowid

    connection.close()

    return {
        "success": True,
        "disposition_logged": status,
        "result_id": result_id,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if not data:
        return jsonify({
            "status": "error",
            "message": "Request body is required"
        }), 400

    message = data.get("message", {})

    if message.get("type") != "tool-calls":
        return jsonify({
            "status": "acknowledged"
        }), 200

    tool_calls = message.get("toolCalls", [])

    if not tool_calls:
        return jsonify({
            "status": "error",
            "message": "No tool calls found"
        }), 400

    results = []

    for tool_call in tool_calls:
        tool_call_id = tool_call.get("id")
        function = tool_call.get("function", {})

        tool_name = function.get("name")
        arguments = function.get("arguments", {})

        if isinstance(arguments, str):
            import json
            arguments = json.loads(arguments)

        print(f"[Tool Call Received]: {tool_name}", arguments)

        if tool_name == "verify_customer":
            result = verify_customer(arguments)

        elif tool_name == "log_promise_to_pay":
            result = log_promise_to_pay(arguments)

        elif tool_name == "send_payment_link":
            result = send_payment_link(arguments)

        elif tool_name == "escalate_to_agent":
            result = escalate_to_agent(arguments)

        elif tool_name == "mark_disposition":
            result = mark_disposition(arguments)

        else:
            result = {
                "success": False,
                "message": f"Unknown function: {tool_name}"
            }

        import json

        results.append({
            "toolCallId": tool_call_id,
            "result": json.dumps(result)
        })

    return jsonify({
        "results": results
    })


@app.route("/call-results", methods=["GET"])
def get_call_results():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            customer_id,
            outcome,
            promised_date,
            notes
        FROM call_results
        ORDER BY id DESC
    """)

    results = [dict(row) for row in cursor.fetchall()]

    connection.close()

    return jsonify({
        "status": "success",
        "results": results
    })


if __name__ == "__main__":
    init_database()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )