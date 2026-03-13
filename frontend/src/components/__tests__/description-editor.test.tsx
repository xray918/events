import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { DescriptionEditor } from "../description-editor";

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("DescriptionEditor", () => {
  it("renders textarea and toolbar buttons", () => {
    render(<DescriptionEditor value="" onChange={vi.fn()} />);
    expect(screen.getByText("活动描述")).toBeInTheDocument();
    expect(screen.getByText("🖼️ 插入图片")).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText("详细介绍你的活动...（支持 Markdown 格式）"),
    ).toBeInTheDocument();
  });

  it("shows AI generate button when onAIGenerate is provided", () => {
    render(
      <DescriptionEditor
        value=""
        onChange={vi.fn()}
        onAIGenerate={vi.fn()}
      />,
    );
    expect(screen.getByText("✨ AI 生成")).toBeInTheDocument();
  });

  it("does not show AI button when onAIGenerate is not provided", () => {
    render(<DescriptionEditor value="" onChange={vi.fn()} />);
    expect(screen.queryByText("✨ AI 生成")).not.toBeInTheDocument();
  });

  it("calls onAIGenerate when AI button clicked", () => {
    const onAI = vi.fn();
    render(
      <DescriptionEditor value="" onChange={vi.fn()} onAIGenerate={onAI} />,
    );
    fireEvent.click(screen.getByText("✨ AI 生成"));
    expect(onAI).toHaveBeenCalledOnce();
  });

  it("shows AI loading state", () => {
    render(
      <DescriptionEditor
        value=""
        onChange={vi.fn()}
        onAIGenerate={vi.fn()}
        aiLoading
      />,
    );
    expect(screen.getByText("AI 生成中...")).toBeInTheDocument();
  });

  it("calls onChange when typing in textarea", () => {
    const onChange = vi.fn();
    render(<DescriptionEditor value="" onChange={onChange} />);
    const textarea = screen.getByPlaceholderText(
      "详细介绍你的活动...（支持 Markdown 格式）",
    );
    fireEvent.change(textarea, { target: { value: "hello" } });
    expect(onChange).toHaveBeenCalledWith("hello");
  });

  it("uploads image and inserts markdown on file select", async () => {
    const onChange = vi.fn();
    global.fetch = vi.fn().mockResolvedValue({
      json: () =>
        Promise.resolve({
          success: true,
          url: "https://cdn.example.com/photo.jpg",
        }),
    });

    render(<DescriptionEditor value="existing text" onChange={onChange} />);

    const file = new File(["img"], "photo.png", { type: "image/png" });
    const input = document.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(
        expect.stringContaining("![photo](https://cdn.example.com/photo.jpg)"),
      );
    });
  });

  it("shows error on upload failure", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      json: () => Promise.resolve({ success: false, detail: "服务器错误" }),
    });

    render(<DescriptionEditor value="" onChange={vi.fn()} />);

    const file = new File(["img"], "photo.png", { type: "image/png" });
    const input = document.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText("服务器错误")).toBeInTheDocument();
    });
  });

  it("rejects non-image files", () => {
    render(<DescriptionEditor value="" onChange={vi.fn()} />);
    const file = new File(["txt"], "readme.txt", { type: "text/plain" });
    const input = document.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });
    expect(screen.getByText("请选择图片文件")).toBeInTheDocument();
  });

  it("rejects files larger than 5MB", () => {
    render(<DescriptionEditor value="" onChange={vi.fn()} />);
    const bigFile = new File(["x".repeat(6 * 1024 * 1024)], "big.png", {
      type: "image/png",
    });
    const input = document.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement;
    fireEvent.change(input, { target: { files: [bigFile] } });
    expect(screen.getByText("图片不能超过 5MB")).toBeInTheDocument();
  });

  it("uploads image on paste from clipboard", async () => {
    const onChange = vi.fn();
    global.fetch = vi.fn().mockResolvedValue({
      json: () =>
        Promise.resolve({
          success: true,
          url: "https://cdn.example.com/pasted.png",
        }),
    });

    render(<DescriptionEditor value="" onChange={onChange} />);

    const textarea = screen.getByPlaceholderText(
      "详细介绍你的活动...（支持 Markdown 格式）",
    );
    const file = new File(["img"], "image.png", { type: "image/png" });
    const pasteEvent = new Event("paste", { bubbles: true });
    Object.defineProperty(pasteEvent, "clipboardData", {
      value: {
        items: [{ type: "image/png", getAsFile: () => file }],
      },
    });
    textarea.dispatchEvent(pasteEvent);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/upload/image"),
        expect.any(Object),
      );
    });
  });

  it("shows hint text about markdown and image support", () => {
    render(<DescriptionEditor value="" onChange={vi.fn()} />);
    expect(
      screen.getByText(/可直接粘贴或拖拽图片到编辑区/),
    ).toBeInTheDocument();
  });
});
