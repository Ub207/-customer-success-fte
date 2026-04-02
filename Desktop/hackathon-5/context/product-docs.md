# TechCorp SaaS - Product Documentation

## Getting Started

### Account Setup
1. Sign up at app.techcorp.io
2. Verify your email address
3. Create your first workspace
4. Invite team members via Settings > Team > Invite

### Password Reset
1. Go to app.techcorp.io/login
2. Click "Forgot Password"
3. Enter your email address
4. Check inbox for reset link (expires in 24 hours)
5. Create new password (min 8 chars, must include number and special character)

### Two-Factor Authentication (2FA)
- Enable via Settings > Security > Two-Factor Authentication
- Supports authenticator apps (Google Authenticator, Authy) and SMS
- Recovery codes available upon setup - store them safely

## Task Management

### Creating Tasks
- Click "+" button or press "C" shortcut
- Required: Title, Assignee, Due Date
- Optional: Priority, Labels, Description, Attachments
- Subtasks: Click "Add subtask" within any task

### Task Priorities
- Urgent: Needs immediate attention
- High: Complete this week
- Medium: Complete this sprint
- Low: Complete when possible

### Recurring Tasks
- Open task > Click "..." > "Make Recurring"
- Options: Daily, Weekly, Monthly, Custom
- Recurrence ends: Never, On date, After N occurrences

### Bulk Actions
- Select multiple tasks: Hold Shift + Click
- Bulk assign, update status, add labels, move to different project

## Integrations

### Slack Integration
1. Go to Settings > Integrations > Slack
2. Click "Connect Slack"
3. Authorize TechCorp in Slack
4. Configure notifications per workspace

### GitHub Integration
- Connects commits and PRs to tasks
- Setup: Settings > Integrations > GitHub
- Link via task description: #TASK-123

### Google Drive Integration
- Attach Drive files directly to tasks
- Setup: Settings > Integrations > Google Drive
- Requires Google Workspace account

### Zapier / Make Integration
- 200+ automation triggers available
- Use API key from Settings > API > Generate Key

## API Documentation

### Authentication
All API calls require authentication header:
```
Authorization: Bearer YOUR_API_KEY
```
API keys: Settings > API > Manage Keys

### Rate Limits
- Starter: 100 requests/minute
- Pro: 1,000 requests/minute
- Enterprise: 5,000 requests/minute
- Rate limit exceeded: HTTP 429, retry after X seconds

### Common Endpoints
- GET /api/v1/tasks - List tasks
- POST /api/v1/tasks - Create task
- PUT /api/v1/tasks/{id} - Update task
- DELETE /api/v1/tasks/{id} - Delete task
- GET /api/v1/projects - List projects
- POST /api/v1/webhooks - Create webhook

### Webhook Events
- task.created, task.updated, task.completed, task.deleted
- project.created, project.archived
- member.invited, member.removed

## Billing & Plans

### Changing Plans
- Upgrade: Takes effect immediately, prorated billing
- Downgrade: Takes effect at end of billing period
- Changes in Settings > Billing > Change Plan

### Payment Methods
- Credit/debit cards (Visa, Mastercard, Amex)
- ACH bank transfer (Enterprise only)
- Invoice billing available for annual Enterprise plans

### Refund Policy
All refund requests must go through billing@techcorp.io. AI agent cannot process refunds.

## Troubleshooting

### App Not Loading
1. Clear browser cache (Ctrl+Shift+Del)
2. Try incognito/private mode
3. Check status.techcorp.io for outages
4. Try a different browser
5. Disable browser extensions

### Sync Issues
- Force sync: Settings > Advanced > Force Sync
- Check internet connection
- Log out and log back in
- Clear app cache

### Missing Notifications
1. Check notification settings: Settings > Notifications
2. Verify email isn't in spam/junk
3. Check browser notification permissions
4. Ensure TechCorp email isn't blocked

### Data Export
- Export tasks: Settings > Data > Export Tasks (CSV/JSON)
- Export reports: Reports > Download
- Full data export: Settings > Data > Request Full Export (24hr processing)
