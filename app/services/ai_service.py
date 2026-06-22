import json
import re
from google import genai
from app.config import settings

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def _generate(prompt: str) -> str:
    client = _get_client()
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )
    return response.text.strip()


def _clean_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    return json.loads(text)


def analyze_financial_health(user_data: dict) -> dict:
    """Calls Gemini to generate health score, risk level, and recommendations."""
    prompt = f"""You are FinWell AI, an expert financial wellness advisor specializing in Indian digital banking.

USER FINANCIAL PROFILE:
- Name: {user_data.get('name')}
- Account Type: {user_data.get('account_type')} (Jan Dhan/Savings/Current/Salary)
- Bank: {user_data.get('bank_name', 'Indian bank')}
- Current Balance: ₹{user_data.get('current_balance', 0):,.2f}
- Minimum Balance Required: ₹{user_data.get('min_balance', 1000):,.2f}
- Buffer above minimum: ₹{user_data.get('current_balance', 0) - user_data.get('min_balance', 1000):,.2f}
- Monthly Income: ₹{user_data.get('monthly_income', 0):,.2f}
- Monthly Debit Total (last 30 days): ₹{user_data.get('monthly_debits', 0):,.2f}
- Monthly Credit Total (last 30 days): ₹{user_data.get('monthly_credits', 0):,.2f}
- Monthly Surplus/Deficit: ₹{user_data.get('monthly_surplus', 0):,.2f}
- Total Penalty Charges (last 90 days): ₹{user_data.get('total_penalties', 0):,.2f}
- Top Spending Categories: {user_data.get('top_categories', [])}
- Recent Transactions Summary: {user_data.get('recent_summary', 'No recent transactions')}

CONTEXT:
- Minimum balance penalty in India ranges from ₹200-₹800/month depending on bank
- Jan Dhan accounts have ₹0 minimum balance
- RBI regulations require banks to notify before charging penalties
- UPI payments are free and instant

Analyze this profile and respond ONLY with valid JSON (no markdown, no explanation):
{{
  "health_score": <integer 0-100>,
  "penalty_risk": "<High|Medium|Low>",
  "risk_details": "<one sentence explaining the risk level>",
  "recommendations": [
    "<actionable tip 1 specific to India>",
    "<actionable tip 2>",
    "<actionable tip 3>"
  ],
  "cash_flow_7days": <predicted net cash flow next 7 days as float>,
  "penalty_savings_potential": <estimated annual penalty savings if advice followed>,
  "ai_summary": "<2-3 sentence personalized summary in friendly tone>"
}}"""

    try:
        if not settings.gemini_api_key:
            return _rule_based_analysis(user_data)
        text = _generate(prompt)
        return _clean_json(text)
    except Exception:
        return _rule_based_analysis(user_data)


def _rule_based_analysis(user_data: dict) -> dict:
    balance = user_data.get("current_balance", 0)
    min_bal = user_data.get("min_balance", 1000)
    surplus = user_data.get("monthly_surplus", 0)

    buffer_pct = (balance - min_bal) / max(min_bal, 1) * 100

    if buffer_pct < 20:
        risk = "High"
        score = max(10, int(buffer_pct))
    elif buffer_pct < 50:
        risk = "Medium"
        score = 40 + int(buffer_pct * 0.4)
    else:
        risk = "Low"
        score = min(95, 60 + int(buffer_pct * 0.2))

    if surplus < 0:
        score = max(5, score - 20)

    return {
        "health_score": score,
        "penalty_risk": risk,
        "risk_details": f"Balance buffer is {buffer_pct:.0f}% above minimum required.",
        "recommendations": [
            "Set up auto-transfer to maintain ₹500 buffer above minimum balance.",
            "Link a sweep-in FD to your savings account to earn interest and avoid penalties.",
            "Use UPI AutoPay for recurring bills to avoid missed payments.",
        ],
        "cash_flow_7days": surplus / 4,
        "penalty_savings_potential": 2400.0,
        "ai_summary": (
            f"Your current balance of ₹{balance:,.0f} is "
            f"{'above' if balance > min_bal else 'below'} the required minimum of ₹{min_bal:,.0f}. "
            f"Penalty risk is {risk}. Follow the recommendations to save on charges."
        ),
    }


def chat_with_advisor(message: str, user_context: dict) -> dict:
    """Conversational AI financial advisor for Indian users."""
    prompt = f"""You are FinWell AI, a friendly financial wellness chatbot for Indian bank account holders.

USER CONTEXT:
- Balance: ₹{user_context.get('current_balance', 0):,.2f}
- Minimum Required: ₹{user_context.get('min_balance', 1000):,.2f}
- Account Type: {user_context.get('account_type', 'savings')}
- Monthly Income: ₹{user_context.get('monthly_income', 0):,.2f}

USER MESSAGE: {message}

Instructions:
- Be helpful, concise, and friendly
- Give India-specific advice (mention UPI, RBI rules, Jan Dhan, etc.)
- Include specific rupee amounts when relevant
- Give 2-3 follow-up suggestions as short questions the user might ask next
- Keep response under 200 words

Respond ONLY with valid JSON:
{{
  "response": "<your helpful response>",
  "suggestions": ["<follow-up question 1>", "<follow-up question 2>", "<follow-up question 3>"]
}}"""

    try:
        if not settings.gemini_api_key:
            raise ValueError("No API key")
        text = _generate(prompt)
        return _clean_json(text)
    except Exception:
        return {
            "response": (
                "I'm here to help you manage your finances better. "
                "To avoid minimum balance penalties, try to keep ₹500-1000 above the required minimum. "
                "Set up UPI AutoPay for recurring bills to never miss a payment."
            ),
            "suggestions": [
                "How can I avoid minimum balance charges?",
                "What is my financial health score?",
                "How to save money on banking fees?",
            ],
        }
