import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ImageUpload } from "../image-upload";

const mockCreateObjectURL = vi.fn(() => "blob:http://localhost/fake-blob-url");
const mockRevokeObjectURL = vi.fn();

beforeEach(() => {
  vi.restoreAllMocks();
  mockCreateObjectURL.mockClear();
  mockRevokeObjectURL.mockClear();
  global.URL.createObjectURL = mockCreateObjectURL;
  global.URL.revokeObjectURL = mockRevokeObjectURL;
});

describe("ImageUpload", () => {
  it("renders upload prompt when no value and no theme", () => {
    render(<ImageUpload value="" onChange={vi.fn()} />);
    expect(screen.getByText("点击或拖拽上传封面图")).toBeInTheDocument();
    expect(screen.getByText("支持 jpg/png/webp，最大 5MB")).toBeInTheDocument();
  });

  it("shows image preview when value is set", () => {
    render(<ImageUpload value="https://example.com/cover.jpg" onChange={vi.fn()} />);
    const img = screen.getByAltText("封面预览") as HTMLImageElement;
    expect(img).toBeInTheDocument();
    expect(img.src).toBe("https://example.com/cover.jpg");
  });

  it("shows theme background when themeStyle is provided and no image", () => {
    const themeStyle = {
      background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
    };
    const { container } = render(
      <ImageUpload value="" onChange={vi.fn()} themeStyle={themeStyle} />
    );
    const uploadArea = container.querySelector("[style]");
    expect(uploadArea).toHaveStyle({
      background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
    });
    expect(screen.queryByText("点击或拖拽上传封面图")).not.toBeInTheDocument();
  });

  it("does NOT show theme background when image value is set", () => {
    const themeStyle = {
      background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
    };
    render(
      <ImageUpload
        value="https://example.com/cover.jpg"
        onChange={vi.fn()}
        themeStyle={themeStyle}
      />
    );
    const img = screen.getByAltText("封面预览") as HTMLImageElement;
    expect(img).toBeInTheDocument();
  });

  it("creates local preview immediately on file select", async () => {
    const onChange = vi.fn();
    global.fetch = vi.fn().mockResolvedValue({
      json: () => Promise.resolve({ success: true, url: "https://cdn.example.com/uploaded.jpg" }),
    });

    render(<ImageUpload value="" onChange={onChange} />);

    const file = new File(["dummy"], "cover.png", { type: "image/png" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;

    fireEvent.change(input, { target: { files: [file] } });

    expect(mockCreateObjectURL).toHaveBeenCalledWith(file);

    await waitFor(() => {
      const img = screen.getByAltText("封面预览") as HTMLImageElement;
      expect(img.src).toBe("blob:http://localhost/fake-blob-url");
    });

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith("https://cdn.example.com/uploaded.jpg");
    });
  });

  it("clears local preview on upload failure", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      json: () => Promise.resolve({ success: false, detail: "上传出错" }),
    });

    render(<ImageUpload value="" onChange={vi.fn()} />);

    const file = new File(["dummy"], "cover.png", { type: "image/png" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;

    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText("上传出错")).toBeInTheDocument();
    });

    expect(screen.getByText("点击或拖拽上传封面图")).toBeInTheDocument();
  });

  it("rejects files larger than 5MB", () => {
    render(<ImageUpload value="" onChange={vi.fn()} />);

    const bigFile = new File(["x".repeat(6 * 1024 * 1024)], "big.png", { type: "image/png" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;

    fireEvent.change(input, { target: { files: [bigFile] } });

    expect(screen.getByText("图片不能超过 5MB")).toBeInTheDocument();
    expect(mockCreateObjectURL).not.toHaveBeenCalled();
  });

  it("rejects non-image files", () => {
    render(<ImageUpload value="" onChange={vi.fn()} />);

    const txtFile = new File(["hello"], "readme.txt", { type: "text/plain" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;

    fireEvent.change(input, { target: { files: [txtFile] } });

    expect(screen.getByText("请选择图片文件")).toBeInTheDocument();
  });
});
