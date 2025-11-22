from locust import HttpUser, task, between
import random
import json

class CVUser(HttpUser):
    wait_time = between(1, 5)

    @task(1)
    def index(self):
        self.client.get("/")

    @task(2)
    def list_jobs(self):
        self.client.get("/jobs")

   
    # @task(1)
    # def upload_cv(self):
    #     # Needs a sample PDF file to upload
    #     pass
