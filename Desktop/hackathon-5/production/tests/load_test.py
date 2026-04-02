"""
Load tests for the Customer Success FTE API using Locust.

Run with:
    locust -f load_test.py --host=http://localhost:8000 --users=100 --spawn-rate=10

Or headless:
    locust -f load_test.py --host=http://localhost:8000 \
        --users=100 --spawn-rate=10 --run-time=2m --headless
"""

import json
import random

from locust import HttpUser, task, between, events


# ---------------------------------------------------------------------------
# Sample data pools
# ---------------------------------------------------------------------------

SAMPLE_NAMES = [
    "Alice Johnson", "Bob Smith", "Carol White", "David Brown",
    "Emma Davis", "Frank Miller", "Grace Wilson", "Henry Moore",
]

SAMPLE_EMAILS = [
    "alice@company.com", "bob@startup.io", "carol@enterprise.co",
    "david@tech.org", "emma@business.net", "frank@corp.io",
]

SAMPLE_SUBJECTS = [
    "Can't reset my password",
    "API rate limit exceeded",
    "How do I add team members?",
    "Task sync issues",
    "Webhook setup help",
    "How to set up recurring tasks?",
    "Data export question",
    "Two-factor authentication help",
]

SAMPLE_MESSAGES = [
    "I've been trying to reset my password but I'm not receiving the email. Can you help?",
    "We're getting HTTP 429 errors on our API. We're on the Pro plan. Is there a way to increase limits?",
    "I need to add new team members to our workspace. How do I do this?",
    "Our tasks aren't syncing properly across devices. This started yesterday.",
    "I'm trying to set up webhooks but I'm not sure which events to listen to for task completion.",
    "We want to create weekly recurring tasks for our team stand-ups. How do we configure this?",
    "How do I export all tasks to CSV? We need to generate a report.",
    "I want to enable two-factor authentication for my account. What are the steps?",
]

SAMPLE_CATEGORIES = ["general", "technical", "account", "bug", "feedback"]
SAMPLE_PRIORITIES = ["low", "medium", "high"]


def random_submission():
    """Generate a random valid support form submission."""
    return {
        "name": random.choice(SAMPLE_NAMES),
        "email": f"user{random.randint(1, 10000)}@loadtest.com",
        "subject": random.choice(SAMPLE_SUBJECTS),
        "category": random.choice(SAMPLE_CATEGORIES),
        "message": random.choice(SAMPLE_MESSAGES),
        "priority": random.choice(SAMPLE_PRIORITIES),
    }


# ---------------------------------------------------------------------------
# Web Form User
# ---------------------------------------------------------------------------

class WebFormUser(HttpUser):
    """
    Simulates customers submitting support tickets via the web form.

    This is the primary load test user, simulating realistic form submissions.
    """

    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks

    @task(10)
    def submit_support_form(self):
        """Submit a valid support form ticket."""
        payload = random_submission()
        with self.client.post(
            "/web-form/submit",
            json=payload,
            catch_response=True,
            name="/web-form/submit",
        ) as response:
            if response.status_code == 201:
                data = response.json()
                if "ticket_id" not in data:
                    response.failure("Response missing ticket_id")
                else:
                    response.success()
            elif response.status_code == 422:
                response.failure(f"Validation error: {response.text[:200]}")
            elif response.status_code == 500:
                response.failure("Server error on form submission")
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(3)
    def check_ticket_status(self):
        """Look up a ticket status (simulates follow-up check)."""
        # Use a fake ticket ID to test the endpoint performance
        fake_ticket_id = f"00000000-0000-0000-0000-{random.randint(100000000000, 999999999999)}"
        with self.client.get(
            f"/web-form/ticket/{fake_ticket_id}",
            catch_response=True,
            name="/web-form/ticket/[id]",
        ) as response:
            if response.status_code in (200, 404):
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(2)
    def customer_lookup(self):
        """Simulate customer lookup by email."""
        email = f"user{random.randint(1, 10000)}@loadtest.com"
        with self.client.get(
            f"/customers/lookup?email={email}",
            catch_response=True,
            name="/customers/lookup",
        ) as response:
            if response.status_code in (200, 404):
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


# ---------------------------------------------------------------------------
# Health Check User
# ---------------------------------------------------------------------------

class HealthCheckUser(HttpUser):
    """
    Simulates monitoring system pinging the health endpoint.
    Uses a very short wait time to generate constant baseline load.
    """

    wait_time = between(0.5, 2)

    @task(20)
    def health_check(self):
        """Ping the health endpoint."""
        with self.client.get(
            "/health",
            catch_response=True,
            name="/health",
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 503:
                response.failure("Service degraded (DB down)")
            else:
                response.failure(f"Unexpected health status: {response.status_code}")

    @task(5)
    def get_channel_metrics(self):
        """Fetch channel metrics (simulates dashboard polling)."""
        with self.client.get(
            "/metrics/channels",
            catch_response=True,
            name="/metrics/channels",
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "metrics" in data:
                    response.success()
                else:
                    response.failure("Metrics response missing 'metrics' key")
            else:
                response.failure(f"Unexpected metrics status: {response.status_code}")


# ---------------------------------------------------------------------------
# Locust Event Hooks
# ---------------------------------------------------------------------------

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("\n[Load Test] Starting Customer Success FTE load test...")
    print(f"[Load Test] Target host: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    stats = environment.stats
    print("\n[Load Test] Load test complete.")
    print(f"[Load Test] Total requests: {stats.total.num_requests}")
    print(f"[Load Test] Total failures: {stats.total.num_failures}")
    failure_rate = (
        stats.total.num_failures / max(stats.total.num_requests, 1) * 100
    )
    print(f"[Load Test] Failure rate: {failure_rate:.2f}%")

    if failure_rate > 5:
        print("[Load Test] WARNING: Failure rate exceeds 5% threshold!")
