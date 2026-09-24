"""Contract coverage for asynchronous job polling and result retrieval."""

from types import SimpleNamespace


class FakeJob:
    status_value = "complete"
    info_value = SimpleNamespace(function="run_evaluation", success=True, result={"f1_macro": 0.8})
    result_info_value = SimpleNamespace(success=True, result={"f1_macro": 0.8})

    def __init__(self, job_id, redis):
        self.job_id = job_id

    async def status(self):
        return self.status_value

    async def info(self):
        return self.info_value

    async def result_info(self):
        return self.result_info_value


def test_job_status_and_result_return_completed_payload(api_client, monkeypatch):
    monkeypatch.setattr("pi_api.routers.jobs.Job", FakeJob)
    monkeypatch.setattr("pi_api.routers.jobs.get_redis_pool", lambda: _redis_pool())

    status = api_client.get("/jobs/JOB-001")
    result = api_client.get("/jobs/JOB-001/result")

    assert status.status_code == 200
    assert status.json()["status"] == "complete"
    assert status.json()["task"] == "run_evaluation"
    assert status.json()["result"] == {"f1_macro": 0.8}
    assert result.status_code == 200
    assert result.json() == {
        "job_id": "JOB-001",
        "status": "complete",
        "result": {"f1_macro": 0.8},
    }


def test_job_result_rejects_incomplete_job(api_client, monkeypatch):
    class RunningJob(FakeJob):
        status_value = "in_progress"

    monkeypatch.setattr("pi_api.routers.jobs.Job", RunningJob)
    monkeypatch.setattr("pi_api.routers.jobs.get_redis_pool", lambda: _redis_pool())

    response = api_client.get("/jobs/JOB-RUNNING/result")

    assert response.status_code == 409
    assert response.json()["detail"]["status"] == "in_progress"


async def _redis_pool():
    return object()
