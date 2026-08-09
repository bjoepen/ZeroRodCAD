import { describe, expect, it } from "vitest";
import { renderStatusRows, statusCssClass, type StatusRow } from "./status";

describe("statusCssClass", () => {
  it("maps READY/RUNNING/CONNECTED to ok", () => {
    expect(statusCssClass("READY")).toBe("ok");
    expect(statusCssClass("RUNNING")).toBe("ok");
    expect(statusCssClass("CONNECTED")).toBe("ok");
  });

  it("maps ERROR to error", () => {
    expect(statusCssClass("ERROR")).toBe("error");
  });

  it("maps STOPPED/NOT_READY/NOT_IMPLEMENTED to neutral", () => {
    expect(statusCssClass("STOPPED")).toBe("neutral");
    expect(statusCssClass("NOT_READY")).toBe("neutral");
    expect(statusCssClass("NOT_IMPLEMENTED")).toBe("neutral");
  });
});

describe("renderStatusRows", () => {
  it("renders one row per entry with label and value", () => {
    const rows: StatusRow[] = [{ id: "shell", label: "Desktop shell", value: "READY" }];
    const html = renderStatusRows(rows);
    expect(html).toContain("Desktop shell");
    expect(html).toContain("READY");
    expect(html).toContain('data-row-id="shell"');
  });

  it("includes the detail span only when detail is provided", () => {
    const withDetail = renderStatusRows([
      { id: "a", label: "A", value: "READY", detail: "v1.0" },
    ]);
    const withoutDetail = renderStatusRows([{ id: "b", label: "B", value: "READY" }]);
    expect(withDetail).toContain("status-detail");
    expect(withDetail).toContain("v1.0");
    expect(withoutDetail).not.toContain("status-detail");
  });

  it("escapes HTML in label and detail to avoid injection from backend text", () => {
    const html = renderStatusRows([
      { id: "x", label: "<script>x</script>", value: "ERROR", detail: "<b>bad</b>" },
    ]);
    expect(html).not.toContain("<script>x</script>");
    expect(html).toContain("&lt;script&gt;");
    expect(html).not.toContain("<b>bad</b>");
    expect(html).toContain("&lt;b&gt;");
  });
});
