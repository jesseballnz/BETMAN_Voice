from locust import HttpUser, between, task


class VoiceUser(HttpUser):
    wait_time = between(0.5, 2)

    @task
    def generate(self):
        self.client.post(
            "/tts",
            headers={"xi-api-key": "change-this-api-key"},
            json={
                "voiceId": "betman-female-presenter",
                "text": "BETMAN load test. Market intelligence with safe CPU fallback.",
                "async_job": True,
            },
        )
