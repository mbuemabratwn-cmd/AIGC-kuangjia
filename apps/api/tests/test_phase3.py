import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import BackgroundTasks, HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main


class Phase3Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_db_path = main.DB_PATH
        self.original_generated_dir = main.GENERATED_DIR
        self.original_poll_initial = main.POLL_INITIAL_DELAY_SECONDS
        self.original_poll_interval = main.POLL_INTERVAL_SECONDS
        self.original_poll_timeout = main.POLL_TIMEOUT_SECONDS

        root = Path(self.tempdir.name)
        main.DB_PATH = root / "app.db"
        main.GENERATED_DIR = root / "generated"
        main.POLL_INITIAL_DELAY_SECONDS = 0
        main.POLL_INTERVAL_SECONDS = 0
        main.POLL_TIMEOUT_SECONDS = 1
        main.initialize_database()

    def tearDown(self) -> None:
        main.DB_PATH = self.original_db_path
        main.GENERATED_DIR = self.original_generated_dir
        main.POLL_INITIAL_DELAY_SECONDS = self.original_poll_initial
        main.POLL_INTERVAL_SECONDS = self.original_poll_interval
        main.POLL_TIMEOUT_SECONDS = self.original_poll_timeout
        self.tempdir.cleanup()

    def save_api_key(self) -> None:
        main.update_settings(
            main.SettingsPayload(
                api_key="test-key",
                default_model=main.GPT_MODEL,
                default_ratio="1:1",
                default_resolution="1K",
                output_dir=str(main.GENERATED_DIR),
                project_dirs=[],
            )
        )

    def test_validate_payload_rejects_invalid_4k_ratio(self) -> None:
        payload = main.JobCreatePayload(prompt="poster", size="1:1", resolution="4K")

        with self.assertRaises(HTTPException) as context:
            main.validate_job_payload(payload)

        self.assertEqual(context.exception.status_code, 422)
        self.assertIn("4K", context.exception.detail)

    def test_validate_payload_rejects_gemini_mask(self) -> None:
        payload = main.JobCreatePayload(
            prompt="edit",
            model=main.GEMINI_MODEL,
            size="1:1",
            mask_url="https://example.com/mask.png",
            image_urls=["https://example.com/image.png"],
        )

        with self.assertRaises(HTTPException) as context:
            main.validate_job_payload(payload)

        self.assertEqual(context.exception.status_code, 422)
        self.assertIn("Gemini Pro", context.exception.detail)

    def test_validate_payload_requires_reference_for_mask(self) -> None:
        payload = main.JobCreatePayload(prompt="edit", mask_url="https://example.com/mask.png")

        with self.assertRaises(HTTPException) as context:
            main.validate_job_payload(payload)

        self.assertEqual(context.exception.status_code, 422)
        self.assertIn("mask_url", context.exception.detail)

    def test_create_job_forces_low_moderation(self) -> None:
        self.save_api_key()
        background_tasks = BackgroundTasks()

        with mock.patch.object(main, "submit_gpt_image_job", return_value="task_123"):
            response = main.create_job(
                main.JobCreatePayload(prompt="castle under stars", size="16:9", resolution="2K"),
                background_tasks,
            )

        self.assertEqual(response["moderation"], "low")
        self.assertEqual(response["status"], "submitted")
        self.assertEqual(response["remote_task_id"], "task_123")
        self.assertEqual(len(background_tasks.tasks), 1)

    def test_submit_payload_uses_low_moderation(self) -> None:
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps(
                    {"data": [{"status": "submitted", "task_id": "task_123"}]}
                ).encode("utf-8")

        def fake_urlopen(request, timeout=30):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse()

        payload = main.validate_job_payload(
            main.JobCreatePayload(prompt="fox", resolution="1K", size="1:1")
        )

        with mock.patch.object(main.urllib_request, "urlopen", side_effect=fake_urlopen):
            task_id = main.submit_gpt_image_job("token", payload)

        self.assertEqual(task_id, "task_123")
        self.assertEqual(captured["body"]["moderation"], "low")

    def test_gemini_payload_uses_documented_shape(self) -> None:
        payload = main.validate_job_payload(
            main.JobCreatePayload(
                prompt="moonlit bamboo path",
                model=main.GEMINI_MODEL,
                size="21:9",
                resolution="4K",
                n=4,
                image_urls=["https://example.com/ref.png"],
            )
        )

        provider_payload = main.build_provider_payload(payload)

        self.assertEqual(provider_payload["model"], main.GEMINI_MODEL)
        self.assertEqual(provider_payload["resolution"], "4K")
        self.assertEqual(provider_payload["n"], 4)
        self.assertNotIn("moderation", provider_payload)
        self.assertNotIn("background", provider_payload)
        self.assertNotIn("output_format", provider_payload)

    def test_gemini_job_can_be_persisted(self) -> None:
        payload = main.validate_job_payload(
            main.JobCreatePayload(
                prompt="moonlit bamboo path",
                model=main.GEMINI_MODEL,
                size="16:9",
                resolution="2K",
            )
        )

        main.create_job_record("job_gemini", payload)
        row = main.get_job_record("job_gemini")
        assert row is not None
        serialized = main.serialize_job(row)

        self.assertEqual(serialized["model"], main.GEMINI_MODEL)
        self.assertEqual(serialized["moderation"], "")

    def test_list_jobs_returns_newest_first(self) -> None:
        first_payload = main.validate_job_payload(
            main.JobCreatePayload(prompt="first", size="1:1", resolution="1K")
        )
        second_payload = main.validate_job_payload(
            main.JobCreatePayload(prompt="second", size="16:9", resolution="2K")
        )

        main.create_job_record("job_a", first_payload)
        main.create_job_record("job_b", second_payload)

        jobs = main.list_jobs()

        self.assertEqual(len(jobs), 2)
        self.assertEqual(jobs[0]["id"], "job_b")
        self.assertEqual(jobs[1]["id"], "job_a")

    def test_process_job_completes_and_saves_paths(self) -> None:
        self.save_api_key()
        payload = main.validate_job_payload(
            main.JobCreatePayload(prompt="mountain sunrise", size="16:9", resolution="4K", n=2)
        )
        job_id = "job_test"
        main.create_job_record(job_id, payload)
        main.update_job_record(job_id, status="submitted", remote_task_id="task_123")

        fake_task = {
            "status": "completed",
            "result": {
                "images": [
                    {"url": ["https://example.com/one.png"]},
                    {"url": ["https://example.com/two.png"]},
                ]
            },
        }

        with mock.patch.object(main, "poll_task_status", return_value=fake_task):
            with mock.patch.object(main, "download_file") as download_file:
                main.process_job(job_id, "token")

        row = main.get_job_record(job_id)
        assert row is not None
        serialized = main.serialize_job(row)
        self.assertEqual(serialized["status"], "completed")
        self.assertEqual(len(serialized["result_paths"]), 2)
        self.assertEqual(download_file.call_count, 2)

    def test_download_job_images_uses_configured_output_dir(self) -> None:
        custom_output_dir = Path(self.tempdir.name) / "custom-output"
        main.update_settings(
            main.SettingsPayload(
                api_key="test-key",
                default_model=main.GPT_MODEL,
                default_ratio="1:1",
                default_resolution="1K",
                output_dir=str(custom_output_dir),
                project_dirs=[],
            )
        )
        fake_task = {
            "result": {
                "images": [
                    {"url": ["https://example.com/one.png"]},
                ]
            }
        }

        with mock.patch.object(main, "download_file") as download_file:
            paths = main.download_job_images("job_custom_dir", fake_task)

        self.assertEqual(Path(paths[0]).parent, custom_output_dir)
        self.assertTrue(custom_output_dir.exists())
        download_file.assert_called_once()

    def test_generated_file_route_reads_configured_output_dir(self) -> None:
        custom_output_dir = Path(self.tempdir.name) / "custom-output"
        custom_output_dir.mkdir()
        image_path = custom_output_dir / "saved.png"
        image_path.write_bytes(b"image")
        main.update_settings(
            main.SettingsPayload(
                api_key="test-key",
                default_model=main.GPT_MODEL,
                default_ratio="1:1",
                default_resolution="1K",
                output_dir=str(custom_output_dir),
                project_dirs=[],
            )
        )

        response = main.get_generated_file("saved.png")

        self.assertEqual(Path(response.path), image_path)

    def test_update_settings_rejects_more_than_four_project_dirs(self) -> None:
        with self.assertRaises(HTTPException) as context:
            main.update_settings(
                main.SettingsPayload(
                    api_key="test-key",
                    default_model=main.GPT_MODEL,
                    default_ratio="1:1",
                    default_resolution="1K",
                    output_dir=str(main.GENERATED_DIR),
                    project_dirs=[
                        main.ProjectDirPayload(name=f"project-{index}", path=str(Path(self.tempdir.name) / str(index)))
                        for index in range(5)
                    ],
                )
            )

        self.assertEqual(context.exception.status_code, 422)

    def test_save_to_project_copies_image(self) -> None:
        source = Path(self.tempdir.name) / "source.png"
        source.write_bytes(b"image")
        project_dir = Path(self.tempdir.name) / "project"
        main.update_settings(
            main.SettingsPayload(
                api_key="test-key",
                default_model=main.GPT_MODEL,
                default_ratio="1:1",
                default_resolution="1K",
                output_dir=str(main.GENERATED_DIR),
                project_dirs=[
                    main.ProjectDirPayload(name="Client", path=str(project_dir)),
                ],
            )
        )

        response = main.save_to_project(
            main.ProjectSavePayload(source_path=str(source), project_name="Client")
        )

        saved_path = Path(response["saved_path"])
        self.assertEqual(saved_path.parent, project_dir)
        self.assertEqual(saved_path.read_bytes(), b"image")

    def test_save_to_project_does_not_overwrite_existing_file(self) -> None:
        source = Path(self.tempdir.name) / "source.png"
        source.write_bytes(b"new")
        project_dir = Path(self.tempdir.name) / "project"
        project_dir.mkdir()
        (project_dir / "source.png").write_bytes(b"old")
        main.update_settings(
            main.SettingsPayload(
                api_key="test-key",
                default_model=main.GPT_MODEL,
                default_ratio="1:1",
                default_resolution="1K",
                output_dir=str(main.GENERATED_DIR),
                project_dirs=[
                    main.ProjectDirPayload(name="Client", path=str(project_dir)),
                ],
            )
        )

        response = main.save_to_project(
            main.ProjectSavePayload(source_path=str(source), project_name="Client")
        )

        self.assertEqual(Path(response["saved_path"]).name, "source_1.png")
        self.assertEqual((project_dir / "source.png").read_bytes(), b"old")

    def test_process_job_marks_failed_when_download_fails(self) -> None:
        self.save_api_key()
        payload = main.validate_job_payload(
            main.JobCreatePayload(prompt="mountain sunrise", size="16:9", resolution="4K")
        )
        job_id = "job_download_failure"
        main.create_job_record(job_id, payload)
        main.update_job_record(job_id, status="submitted", remote_task_id="task_456")

        fake_task = {
            "status": "completed",
            "result": {"images": [{"url": ["https://example.com/one.png"]}]},
        }

        with mock.patch.object(main, "poll_task_status", return_value=fake_task):
            with mock.patch.object(
                main,
                "download_file",
                side_effect=main.ProviderError(502, "Download failed: timeout"),
            ):
                main.process_job(job_id, "token")

        row = main.get_job_record(job_id)
        assert row is not None
        serialized = main.serialize_job(row)
        self.assertEqual(serialized["status"], "failed")
        self.assertEqual(serialized["error_message"], "Download failed: timeout")

    def test_download_file_raises_provider_error_for_os_error(self) -> None:
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b"image-bytes"

        destination = Path(self.tempdir.name) / "nested" / "file.png"

        with mock.patch.object(main.urllib_request, "urlopen", return_value=FakeResponse()):
            with mock.patch.object(
                Path,
                "write_bytes",
                side_effect=OSError("disk full"),
            ):
                with self.assertRaises(main.ProviderError) as context:
                    main.download_file("https://example.com/file.png", destination)

        self.assertIn("disk full", context.exception.message)

    def test_delete_job_removes_record_and_generated_file(self) -> None:
        output_path = Path(self.tempdir.name) / "generated" / "result.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"image")

        payload = main.validate_job_payload(
            main.JobCreatePayload(prompt="delete me", size="1:1", resolution="1K")
        )
        main.create_job_record("job_delete_me", payload)
        main.update_job_record(
            "job_delete_me",
            status="completed",
            result_paths=[str(output_path)],
        )

        response = main.delete_job("job_delete_me")

        self.assertEqual(response["status"], "deleted")
        self.assertFalse(output_path.exists())
        self.assertIsNone(main.get_job_record("job_delete_me"))


if __name__ == "__main__":
    unittest.main()
