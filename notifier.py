"""
Email notification system for high-confidence bets.

Setup in .env:
  NOTIFY_FROM=your_gmail@gmail.com
  NOTIFY_PASSWORD=your_gmail_app_password   # 16-char Google App Password
  NOTIFY_TO=comma,separated,recipients

High-confidence threshold: probability >= 80% AND EV >= 5%

Get a Gmail App Password:
  Google Account → Security → 2-Step Verification → App Passwords
"""

import os
import json
import smtplib
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from pathlib              import Path

SUBSCRIBERS_FILE = Path(__file__).parent / "subscribers.json"
NOTIFY_THRESHOLD_PROB = 0.80
NOTIFY_THRESHOLD_EV   = 0.05


# ── Subscriber management ─────────────────────────────────────────────────────

def load_subscribers() -> list[str]:
    if SUBSCRIBERS_FILE.exists():
        try:
            return json.loads(SUBSCRIBERS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    # Seed from .env NOTIFY_TO if set
    env_to = os.getenv("NOTIFY_TO", "")
    return [e.strip() for e in env_to.split(",") if e.strip()]


def save_subscribers(emails: list[str]):
    SUBSCRIBERS_FILE.write_text(json.dumps(list(set(emails))), encoding="utf-8")


def subscribe(email: str) -> bool:
    email = email.strip().lower()
    if "@" not in email:
        return False
    subs = load_subscribers()
    if email not in subs:
        subs.append(email)
        save_subscribers(subs)
    return True


def unsubscribe(email: str) -> bool:
    subs = load_subscribers()
    new  = [s for s in subs if s != email.strip().lower()]
    save_subscribers(new)
    return len(new) < len(subs)


# ── Email sending ─────────────────────────────────────────────────────────────

def _smtp_config() -> tuple[str, str, str] | None:
    sender   = os.getenv("NOTIFY_FROM", "")
    password = os.getenv("NOTIFY_PASSWORD", "")
    if not sender or not password:
        return None
    return sender, password, sender


def _build_html(bets: list) -> str:
    rows = ""
    for b in bets:
        g = b.game
        sport_colors = {
            "Football":   ("#1a4a3a", "#4ade80"),
            "Basketball": ("#4a2e0a", "#fb923c"),
            "Tennis":     ("#2a1f4a", "#a78bfa"),
        }
        bg, fg = sport_colors.get(g.sport.value, ("#333", "#fff"))
        kick = ""
        if g.kick_off:
            try:
                dt = datetime.datetime.fromisoformat(g.kick_off.replace("Z", "+00:00"))
                kick = dt.strftime("%H:%M UTC")
            except Exception:
                pass

        rows += f"""
        <tr>
          <td style="padding:12px;border-bottom:1px solid #30363d">
            <span style="background:{bg};color:{fg};padding:2px 8px;border-radius:4px;
                         font-size:11px;font-weight:700">{g.sport.value}</span>
            <strong style="margin-left:8px">{g.home_team.name} vs {g.away_team.name}</strong>
            {f'<span style="color:#8b949e;font-size:12px;margin-left:6px">{kick}</span>' if kick else ''}
          </td>
          <td style="padding:12px;border-bottom:1px solid #30363d;color:#f0b429;font-weight:700">
            {b.bet_type.value}
          </td>
          <td style="padding:12px;border-bottom:1px solid #30363d">{b.side}</td>
          <td style="padding:12px;border-bottom:1px solid #30363d;font-weight:700">@{b.odds}</td>
          <td style="padding:12px;border-bottom:1px solid #30363d;
                     color:#3fb950;font-weight:700">{b.probability:.0%}</td>
          <td style="padding:12px;border-bottom:1px solid #30363d;color:#3fb950">
            +{b.expected_value:.1%}
          </td>
        </tr>"""

    date_str = datetime.date.today().strftime("%A, %d %B %Y")
    return f"""
    <html><body style="margin:0;padding:0;background:#0d1117;font-family:Segoe UI,sans-serif;color:#e6edf3">
    <div style="max-width:700px;margin:30px auto;background:#161b22;border:1px solid #30363d;border-radius:10px;overflow:hidden">
      <div style="background:#f0b429;padding:20px 28px">
        <h1 style="margin:0;color:#000;font-size:20px">⚡ High-Confidence Bets — {date_str}</h1>
        <p style="margin:4px 0 0;color:#333;font-size:13px">
          {len(bets)} bet(s) with ≥80% probability and positive expected value
        </p>
      </div>
      <div style="padding:20px 28px">
        <table style="width:100%;border-collapse:collapse;font-size:13px">
          <thead>
            <tr style="color:#8b949e;font-size:11px;text-transform:uppercase;letter-spacing:.05em">
              <th style="padding:8px 12px;text-align:left;border-bottom:2px solid #30363d">Match</th>
              <th style="padding:8px 12px;text-align:left;border-bottom:2px solid #30363d">Bet</th>
              <th style="padding:8px 12px;text-align:left;border-bottom:2px solid #30363d">Selection</th>
              <th style="padding:8px 12px;text-align:left;border-bottom:2px solid #30363d">Odds</th>
              <th style="padding:8px 12px;text-align:left;border-bottom:2px solid #30363d">Prob</th>
              <th style="padding:8px 12px;text-align:left;border-bottom:2px solid #30363d">EV</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
      <div style="padding:16px 28px;background:#0d1117;font-size:11px;color:#8b949e;text-align:center">
        Educational purposes only. Bet responsibly. Check local laws.
        <br><a href="{{unsubscribe_url}}" style="color:#8b949e">Unsubscribe</a>
      </div>
    </div>
    </body></html>"""


def send_alert(bets: list, base_url: str = "") -> dict:
    """
    Send high-confidence bet alert email to all subscribers.
    Returns {sent: N, skipped: reason}.
    """
    cfg = _smtp_config()
    if not cfg:
        return {"sent": 0, "skipped": "NOTIFY_FROM / NOTIFY_PASSWORD not set in .env"}

    qualifying = [b for b in bets
                  if b.probability >= NOTIFY_THRESHOLD_PROB
                  and b.expected_value >= NOTIFY_THRESHOLD_EV]

    if not qualifying:
        return {"sent": 0, "skipped": f"No bets hit ≥{NOTIFY_THRESHOLD_PROB:.0%} threshold"}

    subscribers = load_subscribers()
    if not subscribers:
        return {"sent": 0, "skipped": "No subscribers"}

    sender, password, _ = cfg
    html = _build_html(qualifying)
    date_str = datetime.date.today().strftime("%d %b %Y")
    subject  = f"⚡ {len(qualifying)} High-Confidence Bet(s) Today — {date_str}"

    sent = 0
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            for recipient in subscribers:
                try:
                    msg = MIMEMultipart("alternative")
                    msg["Subject"] = subject
                    msg["From"]    = f"Bet Analyzer <{sender}>"
                    msg["To"]      = recipient
                    unsub_url = f"{base_url}/unsubscribe?email={recipient}"
                    msg.attach(MIMEText(html.replace("{unsubscribe_url}", unsub_url), "html"))
                    server.sendmail(sender, recipient, msg.as_string())
                    sent += 1
                except Exception as e:
                    print(f"[NOTIFY] Failed to send to {recipient}: {e}")
    except Exception as e:
        return {"sent": 0, "skipped": f"SMTP error: {e}"}

    print(f"[NOTIFY] Sent {sent} alert(s) for {len(qualifying)} qualifying bet(s).")
    return {"sent": sent, "qualifying_bets": len(qualifying)}
