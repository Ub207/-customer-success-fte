"""
Knowledge Base Seeder.

Seeds the knowledge_base table with TechCorp product documentation articles.
Run once after the database schema is applied:

    cd /path/to/hackathon-5
    python scripts/seed_knowledge_base.py

Requires DATABASE_URL environment variable (or falls back to localhost default).
"""

import asyncio
import os
import sys

# Allow running from any directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


KNOWLEDGE_ARTICLES = [
    # -----------------------------------------------------------------------
    # Account & Authentication
    # -----------------------------------------------------------------------
    {
        "title": "How to Reset Your Password",
        "category": "account",
        "content": (
            "To reset your TechCorp password:\n"
            "1. Go to app.techcorp.io/login\n"
            "2. Click 'Forgot Password'\n"
            "3. Enter your email address\n"
            "4. Check your inbox for a reset link (expires in 24 hours)\n"
            "5. Create a new password (minimum 8 characters, must include a number and a special character)\n\n"
            "If you don't receive the email within 5 minutes, check your spam folder. "
            "If the problem persists, contact support at support@techcorp.io."
        ),
    },
    {
        "title": "Setting Up Two-Factor Authentication (2FA)",
        "category": "account",
        "content": (
            "Enable 2FA via Settings > Security > Two-Factor Authentication.\n"
            "Supported methods:\n"
            "- Authenticator apps: Google Authenticator, Authy\n"
            "- SMS verification\n\n"
            "Recovery codes are provided upon setup — store them in a safe place.\n"
            "If you lose access to your 2FA device, use a recovery code to sign in, "
            "then disable and re-enable 2FA from Settings > Security."
        ),
    },
    {
        "title": "How to Invite Team Members",
        "category": "account",
        "content": (
            "To invite team members to your workspace:\n"
            "1. Go to Settings > Team > Invite\n"
            "2. Enter the email addresses of the people you want to invite\n"
            "3. Select their role: Admin, Member, or Viewer\n"
            "4. Click 'Send Invitations'\n\n"
            "Invitees receive an email with a link to join. The link expires in 7 days. "
            "You can resend or cancel invitations from Settings > Team > Pending Invitations.\n"
            "Workspace admins can manage roles and remove members at any time."
        ),
    },
    # -----------------------------------------------------------------------
    # Task Management
    # -----------------------------------------------------------------------
    {
        "title": "Creating and Managing Tasks",
        "category": "general",
        "content": (
            "Creating a task:\n"
            "- Click the '+' button in the task list, or press 'C' on your keyboard\n"
            "- Required fields: Title, Assignee, Due Date\n"
            "- Optional: Priority, Labels, Description, Attachments\n"
            "- Add subtasks by clicking 'Add subtask' inside any task\n\n"
            "Task priorities: Urgent, High, Medium, Low\n\n"
            "Moving tasks: Drag and drop between columns, or use the status dropdown.\n"
            "Deleting tasks: Open the task > click '...' > Delete. Deleted tasks are moved to Trash for 30 days."
        ),
    },
    {
        "title": "Setting Up Recurring Tasks",
        "category": "general",
        "content": (
            "To create a recurring task:\n"
            "1. Open the task\n"
            "2. Click '...' (more options)\n"
            "3. Select 'Make Recurring'\n"
            "4. Choose frequency: Daily, Weekly, Monthly, or Custom\n"
            "5. Set end condition: Never, On a specific date, or After N occurrences\n\n"
            "Recurring tasks auto-create the next instance when the current one is completed. "
            "Editing a recurring task gives the option to update just this occurrence or all future ones."
        ),
    },
    {
        "title": "Exporting Tasks to CSV or JSON",
        "category": "general",
        "content": (
            "To export your tasks:\n"
            "1. Go to Settings > Data > Export Tasks\n"
            "2. Choose format: CSV or JSON\n"
            "3. Select date range and project filter (optional)\n"
            "4. Click 'Generate Export'\n"
            "5. Download link will appear — expires after 24 hours\n\n"
            "CSV exports include: title, status, assignee, due date, priority, labels.\n"
            "JSON exports include all fields including subtasks, comments, and attachments metadata."
        ),
    },
    # -----------------------------------------------------------------------
    # API & Integrations
    # -----------------------------------------------------------------------
    {
        "title": "API Rate Limits and How to Handle 429 Errors",
        "category": "technical",
        "content": (
            "TechCorp API rate limits by plan:\n"
            "- Free: 100 requests/hour\n"
            "- Pro: 1,000 requests/hour\n"
            "- Business: 10,000 requests/hour\n"
            "- Enterprise: Custom limits\n\n"
            "When you exceed the limit, the API returns HTTP 429 with a Retry-After header "
            "indicating how many seconds to wait before retrying.\n\n"
            "Best practices:\n"
            "- Implement exponential backoff with jitter\n"
            "- Cache responses where possible\n"
            "- Use webhooks instead of polling for real-time updates\n"
            "- Batch requests using the bulk API endpoints\n\n"
            "To request a rate limit increase, contact support with your use case."
        ),
    },
    {
        "title": "Setting Up Webhooks",
        "category": "technical",
        "content": (
            "TechCorp webhooks let you receive real-time notifications when events happen.\n\n"
            "To configure a webhook:\n"
            "1. Go to Settings > Integrations > Webhooks\n"
            "2. Click 'Add Webhook'\n"
            "3. Enter your endpoint URL (must be HTTPS)\n"
            "4. Select events to subscribe to:\n"
            "   - task.created, task.updated, task.completed, task.deleted\n"
            "   - comment.created\n"
            "   - member.invited, member.removed\n"
            "5. Copy the signing secret to verify webhook payloads\n\n"
            "Webhook payloads are signed with HMAC-SHA256. Verify the X-TechCorp-Signature header. "
            "Failed deliveries are retried up to 5 times with exponential backoff."
        ),
    },
    {
        "title": "API Authentication and API Keys",
        "category": "technical",
        "content": (
            "TechCorp API uses Bearer token authentication.\n\n"
            "To get your API key:\n"
            "1. Go to Settings > API > API Keys\n"
            "2. Click 'Generate New Key'\n"
            "3. Name your key and set an expiry (optional)\n"
            "4. Copy the key immediately — it won't be shown again\n\n"
            "Using the API:\n"
            "Authorization: Bearer YOUR_API_KEY\n\n"
            "API keys can be scoped to specific permissions: read-only, read-write, admin.\n"
            "Rotate keys regularly and revoke old ones from Settings > API > API Keys."
        ),
    },
    # -----------------------------------------------------------------------
    # Billing
    # -----------------------------------------------------------------------
    {
        "title": "Understanding Your Bill and Plan Features",
        "category": "billing",
        "content": (
            "TechCorp plan overview:\n"
            "- Free: Up to 5 users, basic features, 1GB storage\n"
            "- Pro: Up to 25 users, advanced features, 20GB storage, API access\n"
            "- Business: Unlimited users, all features, 100GB storage, priority support\n"
            "- Enterprise: Custom pricing, SSO, audit logs, dedicated support\n\n"
            "Billing is monthly or annual (annual saves 20%).\n"
            "Invoices are emailed on your billing date and available in Settings > Billing > Invoices.\n\n"
            "For pricing questions, refund requests, or plan changes, please contact our billing team — "
            "a human specialist handles all billing matters."
        ),
    },
    # -----------------------------------------------------------------------
    # Troubleshooting
    # -----------------------------------------------------------------------
    {
        "title": "Tasks Not Syncing Across Devices",
        "category": "bug",
        "content": (
            "If tasks are not syncing between devices:\n\n"
            "1. Check your internet connection\n"
            "2. Force-refresh the app:\n"
            "   - Web: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)\n"
            "   - Mobile: Pull down to refresh\n"
            "3. Log out and log back in\n"
            "4. Clear browser cache (Web only): Settings > Clear Cache\n"
            "5. Check the status page at status.techcorp.io for known incidents\n\n"
            "If the issue persists after these steps, please submit a support ticket with:\n"
            "- Your browser/device type and OS version\n"
            "- The specific tasks affected\n"
            "- Approximate time the sync issue started"
        ),
    },
    {
        "title": "Can't Log In — Account Locked or Access Denied",
        "category": "account",
        "content": (
            "If you cannot log in to your TechCorp account:\n\n"
            "Account locked (too many failed attempts):\n"
            "- Wait 15 minutes and try again, OR\n"
            "- Use 'Forgot Password' to reset via email\n\n"
            "SSO/Single Sign-On issues:\n"
            "- Contact your IT administrator to verify your SSO configuration\n"
            "- Ensure your company domain is correctly set up in Settings > Security > SSO\n\n"
            "Access denied to a workspace:\n"
            "- Your workspace admin may have removed your access\n"
            "- Contact your workspace admin to reinstate your membership\n\n"
            "If none of these apply, contact support with your account email and error message."
        ),
    },
    {
        "title": "How to Contact Support and SLA Times",
        "category": "general",
        "content": (
            "TechCorp Support channels:\n"
            "- Web Form: support.techcorp.io (24/7 AI response, human follow-up)\n"
            "- Email: support@techcorp.io\n"
            "- WhatsApp: Available on Business and Enterprise plans\n\n"
            "Response time SLAs by plan:\n"
            "- Free: 24 hours (business days)\n"
            "- Pro: 8 hours (business days)\n"
            "- Business: 4 hours (business days)\n"
            "- Enterprise: 2 hours (24/7)\n\n"
            "For urgent issues (system outages, security incidents), mark your ticket as Urgent. "
            "Our AI assistant handles 80% of queries instantly; complex issues are escalated to specialists."
        ),
    },
]


async def seed():
    """Insert knowledge articles into the database (skips duplicates)."""
    from production.database import get_db_pool, close_db_pool
    import uuid

    pool = await get_db_pool()

    inserted = 0
    skipped = 0

    async with pool.acquire() as conn:
        for article in KNOWLEDGE_ARTICLES:
            # Check if already exists by title
            existing = await conn.fetchval(
                "SELECT id FROM knowledge_base WHERE title = $1",
                article["title"],
            )
            if existing:
                print(f"  SKIP (exists): {article['title']}")
                skipped += 1
                continue

            article_id = str(uuid.uuid4())
            await conn.execute(
                """
                INSERT INTO knowledge_base (id, title, content, category)
                VALUES ($1, $2, $3, $4)
                """,
                article_id,
                article["title"],
                article["content"],
                article["category"],
            )
            print(f"  OK: {article['title']}")
            inserted += 1

    await close_db_pool()
    print(f"\nDone. Inserted: {inserted}  Skipped: {skipped}")


if __name__ == "__main__":
    asyncio.run(seed())
