import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ImageUpload } from "../image-upload";

const mockCreateObjectURL = vi.fn(() => "blob:http://localhost/fake-blob-url");
const mockRevokeObjectURL = vi.fn();

vi.mock("../image-crop-dialog", () => ({
  ImageCropDialog: ({
    onConfirm,
    onCancel,
  }: {
    imageSrc: string;
    onConfirm: (blob: Blob) => void;
    onCancel: () => void;
  }) => (
    <div data-testid="crop-dialog">
      <button data-testid="crop-confirm" onClick={() => onConfirm(new Blob(["cropped"], { type: "image/jpeg" }))}>
        确认裁剪
      </button>
      <button data-testid="crop-cancel" onClick={onCancel}>
        取消
      </button>
    </div>
  ),
}));

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

  it("opens crop dialog on file select, then uploads after crop confirm", async () => {
    const onChange = vi.fn();
    global.fetch = vi.fn().mockResolvedValue({
      json: () => Promise.resolve({ success: true, url: "https://cdn.example.com/uploaded.jpg" }),
    });

    render(<ImageUpload value="" onChange={onChange} />);

    const file = new File(["dummy"], "cover.png", { type: "image/png" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;

    fireEvent.change(input, { target: { files: [file] } });

    expect(mockCreateObjectURL).toHaveBeenCalledWith(file);
    expect(screen.getByTestId("crop-dialog")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("crop-confirm"));

    await waitFor(() => {
      expect(mockCreateObjectURL).toHaveBeenCalledTimes(2);
    });

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith("https://cdn.example.com/uploaded.jpg");
    });
  });

  it("closes crop dialog and does not upload on cancel", () => {
    render(<ImageUpload value="" onChange={vi.fn()} />);

    const file = new File(["dummy"], "cover.png", { type: "image/png" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;

    fireEvent.change(input, { target: { files: [file] } });

    expect(screen.getByTestId("crop-dialog")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("crop-cancel"));

    expect(screen.queryByTestId("crop-dialog")).not.toBeInTheDocument();
    expect(mockRevokeObjectURL).toHaveBeenCalled();
  });

  it("rejects files larger than 5MB without opening crop dialog", () => {
    render(<ImageUpload value="" onChange={vi.fn()} />);

    const bigFile = new File(["x".repeat(6 * 1024 * 1024)], "big.png", { type: "image/png" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;

    fireEvent.change(input, { target: { files: [bigFile] } });

    expect(screen.getByText("图片不能超过 5MB")).toBeInTheDocument();
    expect(screen.queryByTestId("crop-dialog")).not.toBeInTheDocument();
    expect(mockCreateObjectURL).not.toHaveBeenCalled();
  });

  it("rejects non-image files without opening crop dialog", () => {
    render(<ImageUpload value="" onChange={vi.fn()} />);

    const txtFile = new File(["hello"], "readme.txt", { type: "text/plain" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;

    fireEvent.change(input, { target: { files: [txtFile] } });

    expect(screen.getByText("请选择图片文件")).toBeInTheDocument();
    expect(screen.queryByTestId("crop-dialog")).not.toBeInTheDocument();
  });

  it("handles upload failure after crop confirm", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      json: () => Promise.resolve({ success: false, detail: "上传出错" }),
    });

    render(<ImageUpload value="" onChange={vi.fn()} />);

    const file = new File(["dummy"], "cover.png", { type: "image/png" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;

    fireEvent.change(input, { target: { files: [file] } });
    fireEvent.click(screen.getByTestId("crop-confirm"));

    await waitFor(() => {
      expect(screen.getByText("上传出错")).toBeInTheDocument();
    });
  });
});
