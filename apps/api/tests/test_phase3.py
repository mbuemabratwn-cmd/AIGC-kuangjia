import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main


ONE_BY_ONE_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


class CorsTests(unittest.TestCase):
    def test_localhost_and_render_origins_are_allowed(self) -> None:
        middleware = next(
            item for item in main.app.user_middleware if item.cls is main.CORSMiddleware
        )

        self.assertEqual(
            middleware.options["allow_origin_regex"],
            r"^http://(127\.0\.0\.1|localhost):\d+$|^https://[a-z0-9-]+\.onrender\.com$",
        )


class AigcBackendTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_db_path = main.DB_PATH
        self.original_generated_dir = main.GENERATED_DIR
        self.original_reference_asset_dir = main.REFERENCE_ASSET_DIR

        root = Path(self.tempdir.name)
        main.DB_PATH = root / "app.db"
        main.GENERATED_DIR = root / "generated"
        main.REFERENCE_ASSET_DIR = root / "reference-assets"
        main.initialize_database()

    def tearDown(self) -> None:
        main.DB_PATH = self.original_db_path
        main.GENERATED_DIR = self.original_generated_dir
        main.REFERENCE_ASSET_DIR = self.original_reference_asset_dir
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

    def data_url(self, raw_bytes: bytes = ONE_BY_ONE_PNG) -> str:
        encoded = base64.b64encode(raw_bytes).decode("ascii")
        return f"data:image/png;base64,{encoded}"

    def test_validate_payload_rejects_invalid_gpt_4k_ratio(self) -> None:
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

    def test_create_job_forces_gpt_moderation_low_and_completes(self) -> None:
        self.save_api_key()

        with mock.patch.object(
            main,
            "submit_provider_job",
            return_value=[str(main.GENERATED_DIR / "result.png")],
        ):
            response = main.create_job(
                main.JobCreatePayload(prompt="castle under stars", size="16:9", resolution="2K")
            )

        self.assertEqual(response["moderation"], "low")
        self.assertEqual(response["status"], "completed")
        self.assertEqual(response["result_paths"], [str(main.GENERATED_DIR / "result.png")])

    def test_gpt_generation_payload_uses_low_moderation(self) -> None:
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                image = base64.b64encode(b"image").decode("ascii")
                return json.dumps({"data": [{"b64_json": image}]}).encode("utf-8")

        def fake_urlopen(request, timeout=30):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse()

        payload = main.validate_job_payload(
            main.JobCreatePayload(prompt="fox", resolution="1K", size="1:1")
        )

        with mock.patch.object(main.urllib_request, "urlopen", side_effect=fake_urlopen):
            paths = main.submit_gpt_image_job("job_gpt", "token", payload)

        self.assertEqual(captured["body"]["moderation"], "low")
        self.assertEqual(captured["body"]["quality"], "auto")
        self.assertEqual(captured["body"]["n"], 1)
        self.assertEqual(len(paths), 1)

    def test_provider_safety_error_is_actionable(self) -> None:
        body = json.dumps(
            {
                "error": {
                    "message": (
                        "Your request was rejected by the safety system. "
                        "safety_violations=[sexual]. "
                        "(request id: 2026050820290151260404516907797)"
                    )
                }
            }
        )

        message = main.format_provider_error(main.parse_provider_error(body, "Bad Request"))

        self.assertIn("内容安全审核拦截", message)
        self.assertIn("违规类型：sexual", message)
        self.assertIn("请求ID：2026050820290151260404516907797", message)

    def test_vip_generation_payload_requests_base64_and_does_not_send_unsupported_quality_or_n(self) -> None:
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps({"data": [{"url": "https://example.com/result.png"}]}).encode(
                    "utf-8"
                )

        def fake_urlopen(request, timeout=30):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse()

        payload = main.validate_job_payload(
            main.JobCreatePayload(
                prompt="fox",
                model=main.GPT_VIP_MODEL,
                resolution="4K",
                size="3:4",
                n=4,
                quality="high",
            )
        )

        with mock.patch.object(main.urllib_request, "urlopen", side_effect=fake_urlopen):
            with mock.patch.object(main, "download_file") as download_file:
                main.submit_gpt_image_job("job_vip", "token", {**payload, "n": 1})

        self.assertEqual(captured["body"]["model"], main.GPT_VIP_MODEL)
        self.assertEqual(captured["body"]["size"], "2480x3312")
        self.assertEqual(captured["body"]["response_format"], "b64_json")
        self.assertNotIn("quality", captured["body"])
        self.assertNotIn("n", captured["body"])
        download_file.assert_called_once()

    def test_gpt_reference_images_use_edit_endpoint_image_array_in_order(self) -> None:
        captured = {}
        image_a = self.data_url(b"image-a")
        image_b = self.data_url(b"image-b")
        payload = main.validate_job_payload(
            main.JobCreatePayload(
                prompt="use references",
                model=main.GPT_MODEL,
                size="16:9",
                resolution="2K",
                image_urls=[image_a, image_b],
            )
        )
        prepared, _ = main.prepare_provider_assets("job_refs", payload)

        def fake_encode(fields, files):
            captured["fields"] = fields
            captured["files"] = files
            return b"body", "multipart/form-data; boundary=test"

        with mock.patch.object(main, "encode_multipart_form_data", side_effect=fake_encode):
            with mock.patch.object(main, "perform_json_request", return_value={"data": []}):
                with self.assertRaises(main.ProviderError):
                    main.submit_gpt_image_edit_job("job_refs", "token", prepared)

        self.assertIn(("moderation", "low"), captured["fields"])
        self.assertIn(("quality", "auto"), captured["fields"])
        self.assertEqual([file[0] for file in captured["files"]], ["image[]", "image[]"])
        self.assertEqual([file[3] for file in captured["files"]], [b"image-a", b"image-b"])

    def test_vip_reference_images_use_edit_endpoint_image_field_and_resolved_size(self) -> None:
        captured = {}
        payload = main.validate_job_payload(
            main.JobCreatePayload(
                prompt="use references",
                model=main.GPT_VIP_MODEL,
                size="3:4",
                resolution="4K",
                image_urls=[self.data_url(b"image-a"), self.data_url(b"image-b")],
            )
        )
        prepared, _ = main.prepare_provider_assets("job_vip_refs", payload)

        def fake_encode(fields, files):
            captured["fields"] = fields
            captured["files"] = files
            return b"body", "multipart/form-data; boundary=test"

        with mock.patch.object(main, "encode_multipart_form_data", side_effect=fake_encode):
            with mock.patch.object(main, "perform_json_request", return_value={"data": []}):
                with self.assertRaises(main.ProviderError):
                    main.submit_gpt_image_edit_job("job_vip_refs", "token", prepared)

        self.assertIn(("size", "2480x3312"), captured["fields"])
        self.assertIn(("response_format", "b64_json"), captured["fields"])
        self.assertNotIn(("quality", "auto"), captured["fields"])
        self.assertEqual([file[0] for file in captured["files"]], ["image", "image"])
        self.assertEqual([file[3] for file in captured["files"]], [b"image-a", b"image-b"])

    def test_gemini_payload_sends_local_reference_assets_as_inline_data(self) -> None:
        stable_url = main.persist_reference_asset(b"image-a", "image/png")
        payload = main.validate_job_payload(
            main.JobCreatePayload(
                prompt="moonlit bamboo path",
                model=main.GEMINI_MODEL,
                size="21:9",
                resolution="4K",
                image_urls=[stable_url],
            )
        )
        prepared, _ = main.prepare_provider_assets("job_gemini", payload)

        provider_payload = main.build_gemini_request_payload(prepared)
        parts = provider_payload["contents"][0]["parts"]

        self.assertEqual(parts[0], {"text": "moonlit bamboo path"})
        self.assertIn("inlineData", parts[1])
        self.assertEqual(parts[1]["inlineData"]["mimeType"], "image/png")
        self.assertEqual(base64.b64decode(parts[1]["inlineData"]["data"]), b"image-a")
        self.assertEqual(
            provider_payload["generationConfig"]["imageConfig"],
            {"aspectRatio": "21:9", "imageSize": "4K"},
        )

    def test_gemini_payload_downloads_remote_reference_urls_as_inline_data(self) -> None:
        payload = main.validate_job_payload(
            main.JobCreatePayload(
                prompt="moonlit bamboo path",
                model=main.GEMINI_MODEL,
                size="16:9",
                resolution="2K",
                image_urls=["https://example.com/ref.png"],
            )
        )

        with mock.patch.object(
            main,
            "download_reference_image",
            return_value=("image/png", b"remote-image"),
        ) as download_reference_image:
            provider_payload = main.build_gemini_request_payload(payload)

        download_reference_image.assert_called_once_with("https://example.com/ref.png")
        part = provider_payload["contents"][0]["parts"][1]
        self.assertEqual(part["inlineData"]["mimeType"], "image/png")
        self.assertEqual(base64.b64decode(part["inlineData"]["data"]), b"remote-image")

    def test_gemini_submit_uses_bearer_authorization(self) -> None:
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                image = base64.b64encode(b"image").decode("ascii")
                return json.dumps(
                    {
                        "candidates": [
                            {
                                "content": {
                                    "parts": [
                                        {
                                            "inlineData": {
                                                "mimeType": "image/png",
                                                "data": image,
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                ).encode("utf-8")

        def fake_urlopen(request, timeout=30):
            captured["authorization"] = request.headers.get("Authorization")
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse()

        payload = main.validate_job_payload(
            main.JobCreatePayload(
                prompt="moonlit bamboo path",
                model=main.GEMINI_MODEL,
                size="16:9",
                resolution="2K",
            )
        )

        with mock.patch.object(main.urllib_request, "urlopen", side_effect=fake_urlopen):
            paths = main.submit_gemini_image_job("job_gemini_submit", "token", payload)

        self.assertEqual(captured["authorization"], "Bearer token")
        self.assertEqual(captured["body"]["generationConfig"]["imageConfig"]["aspectRatio"], "16:9")
        self.assertEqual(len(paths), 1)

    def test_reference_asset_persistence_deduplicates_by_content_hash(self) -> None:
        first = main.persist_reference_asset(b"same-image", "image/png")
        second = main.persist_reference_asset(b"same-image", "image/png")

        self.assertEqual(first, second)
        self.assertEqual(len(list(main.REFERENCE_ASSET_DIR.iterdir())), 1)

    def test_prepare_provider_assets_preserves_reference_order_and_history_urls(self) -> None:
        payload = main.validate_job_payload(
            main.JobCreatePayload(
                prompt="ordered references",
                model=main.GPT_MODEL,
                size="16:9",
                resolution="2K",
                image_urls=[self.data_url(b"first"), self.data_url(b"second")],
            )
        )

        prepared, _ = main.prepare_provider_assets("job_order", payload)
        main.create_job_record("job_order", prepared, [])
        row = main.get_job_record("job_order")
        assert row is not None
        serialized = main.serialize_job(row)

        self.assertEqual([image["raw_bytes"] for image in prepared["provider_images"]], [b"first", b"second"])
        self.assertEqual(serialized["image_urls"], payload["image_urls"])
        self.assertEqual(serialized["reference_image_urls"], prepared["image_urls"])

    def test_list_job_serializer_uses_stable_reference_urls_to_keep_history_light(self) -> None:
        raw_data_url = self.data_url(b"large-inline-reference")
        payload = main.validate_job_payload(
            main.JobCreatePayload(
                prompt="history list",
                model=main.GPT_MODEL,
                size="16:9",
                resolution="2K",
                image_urls=[raw_data_url],
            )
        )
        prepared, _ = main.prepare_provider_assets("job_light_history", payload)
        main.create_job_record("job_light_history", prepared, [])
        row = main.get_job_record("job_light_history")
        assert row is not None

        detail = main.serialize_job(row)
        listed = main.serialize_job_for_list(row)

        self.assertEqual(detail["image_urls"], [raw_data_url])
        self.assertEqual(listed["image_urls"], prepared["image_urls"])
        self.assertEqual(listed["reference_image_urls"], prepared["image_urls"])

    def test_job_serializer_rewrites_old_local_reference_asset_ports(self) -> None:
        old_reference_url = "http://127.0.0.1:8000/reference-assets/old.png"
        payload = main.validate_job_payload(
            main.JobCreatePayload(
                prompt="old reference url",
                model=main.GPT_MODEL,
                size="16:9",
                resolution="2K",
            )
        )
        main.create_job_record("job_old_ref", payload, [])
        with main.get_connection() as connection:
            connection.execute(
                "UPDATE jobs SET image_urls = ?, reference_image_urls = ? WHERE id = ?",
                (json.dumps([old_reference_url]), json.dumps([old_reference_url]), "job_old_ref"),
            )
            connection.commit()
        row = main.get_job_record("job_old_ref")
        assert row is not None

        serialized = main.serialize_job(row)

        self.assertTrue(main.LOCAL_API_BASE_URL.endswith(":38381"))
        self.assertEqual(
            serialized["reference_image_urls"],
            [main.build_reference_asset_url("old.png")],
        )
        self.assertIn(":38381/reference-assets/", serialized["reference_image_urls"][0])
        self.assertEqual(serialized["image_urls"], [main.build_reference_asset_url("old.png")])

    def test_generated_image_url_can_be_reused_as_reference(self) -> None:
        generated_url = f"{main.LOCAL_API_BASE_URL}/generated/result.png"
        payload = main.validate_job_payload(
            main.JobCreatePayload(
                prompt="reuse generated image",
                model=main.GPT_MODEL,
                size="16:9",
                resolution="2K",
                image_urls=[generated_url],
            )
        )

        with mock.patch.object(
            main,
            "download_reference_image",
            return_value=("image/png", b"generated-image"),
        ) as download_reference_image:
            prepared, _ = main.prepare_provider_assets("job_generated_ref", payload)

        download_reference_image.assert_called_once_with(generated_url)
        self.assertEqual(prepared["provider_images"][0]["raw_bytes"], b"generated-image")
        self.assertEqual(prepared["image_urls"], [generated_url])

    def test_multiple_image_count_runs_provider_once_per_image(self) -> None:
        calls: list[str] = []
        payload = main.validate_job_payload(
            main.JobCreatePayload(
                prompt="four images",
                model=main.GPT_VIP_MODEL,
                size="1:1",
                resolution="1K",
                n=4,
            )
        )

        def fake_submit(job_id, api_key, single_payload):
            calls.append(job_id)
            self.assertEqual(single_payload["n"], 1)
            return [str(main.GENERATED_DIR / f"{job_id}.png")]

        with mock.patch.object(main, "submit_single_provider_job", side_effect=fake_submit):
            result_paths = main.submit_provider_job("job_multi", "token", payload)

        self.assertEqual(len(calls), 4)
        self.assertEqual(len(result_paths), 4)

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
                        main.ProjectDirPayload(
                            name=f"project-{index}",
                            path=str(Path(self.tempdir.name) / str(index)),
                        )
                        for index in range(5)
                    ],
                )
            )

        self.assertEqual(context.exception.status_code, 422)

    def test_save_to_project_copies_image_without_overwriting(self) -> None:
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
        self.assertEqual((project_dir / "source_1.png").read_bytes(), b"new")

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
        main.create_job_record("job_delete_me", payload, [])
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
