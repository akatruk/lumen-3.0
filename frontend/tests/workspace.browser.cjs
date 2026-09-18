// Start Vite first. PLAYWRIGHT_MODULE may point at an existing Playwright installation.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const assert = require("node:assert/strict");
const seed = require("./fixtures/workspace.cjs");
const baseURL = process.env.WORKSPACE_URL || "http://127.0.0.1:5192";
(async () => {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  try {
    for (const scenario of [
      "studio",
      "other-project",
      "legacy",
      "processing",
      "failure",
    ]) {
      const page = await browser.newPage({
        viewport: { width: 1440, height: 1000 },
        reducedMotion: "reduce",
      });
      const data = structuredClone(seed),
        writes = [],
        errors = [];
      if (scenario === "other-project") data.project.id = "f".repeat(32);
      if (scenario === "legacy") data.project.studio = false;
      if (scenario === "processing") {
        data.project.status = "analyzing";
        data.project.stage = "preparing";
        data.project.result = null;
        data.project.analysis = null;
        data.project.metadata.preview_ready = false;
        data.studio.plan = null;
        data.dubbing.versions = [];
      }
      if (scenario === "failure") {
        data.project.status = "failed";
        data.project.error = "worker_interrupted";
      }
      const pid = data.project.id;
      page.on("pageerror", (e) => errors.push(e.message));
      await page.addInitScript(() =>
        localStorage.setItem("lumen_language", "ru"),
      );
      await page.route("**/api/**", async (route) => {
        const request = route.request(),
          path = new URL(request.url()).pathname;
        if (path.includes("/media/") || path.endsWith("/video.mp4"))
          return route.fulfill(
            process.env.WORKSPACE_MEDIA
              ? { path: process.env.WORKSPACE_MEDIA, contentType: "video/mp4" }
              : { status: 204 },
          );
        if (request.method() !== "GET") {
          const body = request.postDataJSON();
          writes.push({ path, method: request.method(), body });
          if (path.endsWith("/manual") && request.method() === "PUT") {
            data.manual.edit = body.edit;
            data.manual.revision++;
            data.studio.revision = data.manual.revision;
            return route.fulfill({ json: data.manual });
          }
          return route.fulfill({ json: { ok: true } });
        }
        let json = [];
        if (path === "/api/session") json = { email: "workspace@example.test" };
        else if (path === "/api/projects") json = [data.project];
        else if (path === `/api/projects/${pid}`) json = data.project;
        else if (path === `/api/studio/projects/${pid}`) json = data.studio;
        else if (path.endsWith("/manual/summary")) json = {revision:data.manual.revision,source_duration:12,output_duration:12,removed_seconds:0,removed_ranges:[],near_original:false,captions:0,music:false,normalize:false,global_operations:[],pending_proposals:{creative:3,music:0,individual:0},clips:data.manual.edit.clips.map((c,i)=>({...c,source_start:c.start,source_end:c.end,operations:i===0?['motion']:[]}))};
        else if (path.endsWith("/manual")) json = data.manual;
        else if (path.endsWith("/dubbing")) json = data.dubbing;
        return route.fulfill({ json });
      });
      await page.goto(`${baseURL}/#project/${pid}`);
      await page.locator(".ws-heading h1").waitFor();
      assert.equal(await page.locator(".project-workspace").count(), 1);
      if (scenario === "studio" || scenario === "other-project") {
        await page.locator(".ws-scenes button").first().waitFor();
        assert.equal(await page.locator(".manual-clip:visible").count(), 1);
        await page
          .locator(".ws-heading")
          .getByRole("button", { name: /Версии/ })
          .click();
        assert.equal(await page.locator("dialog[open] article").count(), 4);
        const row = page.locator("dialog[open] article").nth(1);
        const download = await row.locator("a").getAttribute("href");
        await row.locator("button").click();
        assert.equal(
          await page.locator(".ws-header-download").getAttribute("href"),
          download,
        );
        assert.equal(
          await page.locator(".ws-preview-meta a").getAttribute("href"),
          download,
        );
        assert.equal(await page.locator("video:visible").count(), 1);
        const compare = page.getByRole("button", {
          name: "Сравнить с исходником",
          exact: true,
        });
        await compare.click();
        assert.match(
          await page.locator(".ws-ready-player video").getAttribute("src"),
          /media\/source/,
        );
        await compare.click();
        assert.match(
          await page.locator(".ws-ready-player video").getAttribute("src"),
          /dubbing/,
        );

        await page
          .locator(".ws-tools")
          .getByRole("button", { name: "Эффекты", exact: true })
          .click();
        await page
          .getByRole("button", { name: "Плавное приближение", exact: true })
          .click();
        assert.equal(await page.locator(".ws-draft-slot").isVisible(), true);
        assert.match(
          await page.locator(".ws-footer").innerText(),
          /Сцен для проверки: 1/,
        );
        await page
          .locator(".ws-tools")
          .getByRole("button", { name: "Субтитры", exact: true })
          .click();
        await page
          .getByLabel("Встроить отредактированные субтитры в видео")
          .uncheck();
        await page
          .locator(".ws-tools")
          .getByRole("button", { name: "Звук", exact: true })
          .click();
        await page.getByLabel("Язык озвучки").selectOption("en");
        await page
          .locator(".ws-tools")
          .getByRole("button", { name: "Эффекты", exact: true })
          .click();
        const clip = page.locator(".manual-clip:visible");
        await clip.getByLabel("Утвердить", { exact: true }).check();
        await page
          .getByRole("button", { name: "Сохранить ручные правки", exact: true })
          .click();
        await page
          .getByRole("button", {
            name: "Проверить и создать версию",
            exact: true,
          })
          .click();
        assert.equal(
          writes.filter((r) => r.path.endsWith("/render")).length,
          0,
        );
        await page.locator('.render-summary').waitFor();
        assert.match(await page.locator('.render-summary').innerText(), /Неприменённые предложения AI: 3/);
        assert.match(await page.locator('.render-summary').innerText(), /Движение камеры/);
        assert.equal(writes[0].body.edit.clips[0].zoom_end, 1.2);
        assert.equal(writes[0].body.edit.subtitles, false);
        assert.equal(writes[0].path, `/api/studio/projects/${pid}/manual`);
        await page
          .getByRole("button", { name: "Создать видео с этими изменениями", exact: true })
          .click();
        assert.equal(writes.at(-1).body.revision, 2);
        assert.equal(
          writes.at(-1).path,
          `/api/studio/projects/${pid}/manual/render`,
        );
        await page
          .locator(".ws-tools")
          .getByRole("button", { name: "Звук", exact: true })
          .click();
        assert.equal(await page.getByLabel("Язык озвучки").inputValue(), "en");
        await page.setViewportSize({ width: 390, height: 844 });
        for (const name of [
          "Монтаж",
          "Субтитры",
          "Звук",
          "Эффекты",
          "Материалы",
          "Проверка",
        ]) {
          await page
            .locator(".ws-tools")
            .getByRole("button", { name, exact: true })
            .click();
          assert.equal(
            await page.evaluate(
              () => document.documentElement.scrollWidth <= innerWidth,
            ),
            true,
            name,
          );
        }
        await page
          .locator(".ws-heading")
          .getByRole("button", { name: /Версии/ })
          .click();
        await page.keyboard.press("Escape");
        assert.equal(await page.locator("dialog[open]").count(), 0);
      } else if (scenario === "legacy") {
        await page.locator(".ws-scenes button").first().click();
        assert.match(
          await page.locator(".ws-ready-player video").getAttribute("src"),
          /media\/source/,
        );
        assert.equal(await page.locator("video:visible").count(), 1);
      } else if (scenario === "processing") {
        assert.equal(await page.locator(".ws-header-download").count(), 0);
        assert.equal(await page.locator("video:visible").count(), 0);
        assert.match(
          await page.locator(".ws-inspector").innerText(),
          /после анализа/,
        );
      } else if (scenario === "failure") {
        assert.equal(await page.locator(".ws-header-download").count(), 1);
        assert.match(
          await page.locator(".ws-preview").innerText(),
          /Готовые версии сохранены/,
        );
      }
      assert.deepEqual(errors, [], scenario);
      await page.close();
      console.log("PASS", scenario);
    }
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e.message);
  process.exitCode = 1;
});
