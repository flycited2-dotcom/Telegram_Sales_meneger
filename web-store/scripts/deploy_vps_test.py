import unittest

from scripts.deploy_vps import build_connect_kwargs, build_remote_deploy_script, should_include_archive_path


class DeployVpsTests(unittest.TestCase):
    def test_archive_excludes_local_builds_dependencies_and_secrets(self):
        excluded = [
            ".env",
            ".env.local",
            ".next/BUILD_ID",
            "node_modules/next/package.json",
            "dev-server.out.log",
            "__pycache__/deploy.pyc",
        ]
        for path in excluded:
            with self.subTest(path=path):
                self.assertFalse(should_include_archive_path(path))

        included = [
            "src/app/catalog/catalog-view.tsx",
            "package.json",
            "package-lock.json",
            "scripts/sync-products.ts",
            "HANDOFF.md",
        ]
        for path in included:
            with self.subTest(path=path):
                self.assertTrue(should_include_archive_path(path))

    def test_remote_script_builds_before_restart_and_checks_health(self):
        script = build_remote_deploy_script(
            remote_root="/var/www/climat-simf.ru",
            process_name="climat-simf-store",
            build_log="/tmp/climat-build.log",
            run_install=False,
        )

        build_index = script.index("npm run build")
        manifest_index = script.index(".next/prerender-manifest.json")
        restart_index = script.index("pm2 delete climat-simf-store")
        health_index = script.index("curl -fsS -m 30 http://127.0.0.1:3001/")

        self.assertLess(build_index, manifest_index)
        self.assertLess(manifest_index, restart_index)
        self.assertLess(restart_index, health_index)
        self.assertIn("set -euo pipefail", script)

    def test_connect_kwargs_support_key_auth_without_password(self):
        kwargs = build_connect_kwargs(
            host="212.116.115.150",
            user="root",
            key_path="C:/Users/user/.ssh/climat_simf_deploy",
            password=None,
        )

        self.assertEqual(kwargs["hostname"], "212.116.115.150")
        self.assertEqual(kwargs["username"], "root")
        self.assertEqual(kwargs["key_filename"], "C:/Users/user/.ssh/climat_simf_deploy")
        self.assertNotIn("password", kwargs)


if __name__ == "__main__":
    unittest.main()
