import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { RegisterButton } from "../register-button";
import { QuestionConfigurator } from "../question-configurator";

// ─────────────────────────────────────────────
// RegisterButton – 其他选项 & 文本输入
// ─────────────────────────────────────────────

const mockSelectQuestion = {
  id: "q1",
  question_text: "你是如何了解到本活动的？",
  question_type: "select",
  options: ["朋友推荐", "社交媒体", "其他（请说明）"],
  is_required: true,
};

const mockMultiQuestion = {
  id: "q2",
  question_text: "是否使用以下产品",
  question_type: "multiselect",
  options: ["QClaw", "MaxClaw", "其他（请说明）"],
  is_required: true,
};

function setupFetch(registered = false) {
  global.fetch = vi.fn().mockImplementation((url: string) => {
    if (url.includes("/registration") && !url.includes("register")) {
      return Promise.resolve({
        json: () => Promise.resolve({ registered }),
      });
    }
    return Promise.resolve({
      json: () => Promise.resolve({ success: true, data: { registration_id: "r1", status: "approved", qr_code_token: "tok", message: "报名成功！" } }),
    });
  });
}

async function openForm(questions: typeof mockSelectQuestion[]) {
  setupFetch(false);
  render(
    <RegisterButton
      slug="test-event"
      questions={questions}
      eventStatus="published"
    />,
  );
  await waitFor(() => expect(screen.queryByText("立即报名")).toBeInTheDocument());
  fireEvent.click(screen.getByText("立即报名"));
  await waitFor(() => expect(screen.getByText("报名信息")).toBeInTheDocument());
}

describe("RegisterButton – 其他（请说明）单选", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("选中其他选项后显示文本输入框", async () => {
    await openForm([mockSelectQuestion]);
    const otherRadio = screen.getByRole("radio", { name: "其他（请说明）" });
    fireEvent.click(otherRadio);
    await waitFor(() =>
      expect(screen.getByPlaceholderText("请说明...")).toBeInTheDocument(),
    );
  });

  it("未选其他时不显示文本输入框", async () => {
    await openForm([mockSelectQuestion]);
    expect(screen.queryByPlaceholderText("请说明...")).not.toBeInTheDocument();
  });

  it("选其他但不填说明时提交被阻止", async () => {
    await openForm([mockSelectQuestion]);
    const otherRadio = screen.getByRole("radio", { name: "其他（请说明）" });
    fireEvent.click(otherRadio);
    fireEvent.click(screen.getByText("提交报名"));
    await waitFor(() =>
      expect(screen.getByText(/请填写.*其他.*的具体说明/)).toBeInTheDocument(),
    );
  });

  it("填写说明后提交成功，答案合并为其他：xxx", async () => {
    await openForm([mockSelectQuestion]);
    const otherRadio = screen.getByRole("radio", { name: "其他（请说明）" });
    fireEvent.click(otherRadio);
    await waitFor(() => screen.getByPlaceholderText("请说明..."));
    fireEvent.change(screen.getByPlaceholderText("请说明..."), {
      target: { value: "通过微信群" },
    });
    fireEvent.click(screen.getByText("提交报名"));
    await waitFor(() => {
      const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
      const registerCall = fetchMock.mock.calls.find((c: unknown[]) =>
        (c[0] as string).includes("/register"),
      );
      expect(registerCall).toBeDefined();
      const body = JSON.parse((registerCall![1] as { body: string }).body);
      expect(body.custom_answers.q1).toBe("其他：通过微信群");
    });
  });
});

describe("RegisterButton – 其他（请说明）多选", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("勾选其他选项后显示文本输入框", async () => {
    await openForm([mockMultiQuestion]);
    const otherCheckbox = screen.getByRole("checkbox", { name: "其他（请说明）" });
    fireEvent.click(otherCheckbox);
    await waitFor(() =>
      expect(screen.getByPlaceholderText("请说明...")).toBeInTheDocument(),
    );
  });

  it("填写说明后提交，多选答案包含其他：xxx", async () => {
    await openForm([mockMultiQuestion]);
    fireEvent.click(screen.getByRole("checkbox", { name: "QClaw" }));
    const otherCheckbox = screen.getByRole("checkbox", { name: "其他（请说明）" });
    fireEvent.click(otherCheckbox);
    await waitFor(() => screen.getByPlaceholderText("请说明..."));
    fireEvent.change(screen.getByPlaceholderText("请说明..."), {
      target: { value: "自研产品" },
    });
    fireEvent.click(screen.getByText("提交报名"));
    await waitFor(() => {
      const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
      const registerCall = fetchMock.mock.calls.find((c: unknown[]) =>
        (c[0] as string).includes("/register"),
      );
      expect(registerCall).toBeDefined();
      const body = JSON.parse((registerCall![1] as { body: string }).body);
      expect(body.custom_answers.q2).toContain("QClaw");
      expect(body.custom_answers.q2).toContain("其他：自研产品");
    });
  });
});

// ─────────────────────────────────────────────
// QuestionConfigurator – + 其他选项 快捷按钮
// ─────────────────────────────────────────────

describe("QuestionConfigurator – 其他选项快捷按钮", () => {
  it("单选/多选题显示 + 其他选项 按钮", () => {
    const onChange = vi.fn();
    render(
      <QuestionConfigurator
        value={[{ question_text: "测试题", question_type: "select", options: [], is_required: false }]}
        onChange={onChange}
      />,
    );
    expect(screen.getByText("+ 其他选项")).toBeInTheDocument();
  });

  it("文本题不显示 + 其他选项 按钮", () => {
    render(
      <QuestionConfigurator
        value={[{ question_text: "文本题", question_type: "text", options: [], is_required: false }]}
        onChange={vi.fn()}
      />,
    );
    expect(screen.queryByText("+ 其他选项")).not.toBeInTheDocument();
  });

  it("点击 + 其他选项 会添加「其他（请说明）」选项", () => {
    const onChange = vi.fn();
    render(
      <QuestionConfigurator
        value={[{ question_text: "测试题", question_type: "select", options: ["选项A"], is_required: false }]}
        onChange={onChange}
      />,
    );
    fireEvent.click(screen.getByText("+ 其他选项"));
    expect(onChange).toHaveBeenCalledWith([
      expect.objectContaining({ options: ["选项A", "其他（请说明）"] }),
    ]);
  });

  it("已有「其他（请说明）」时，+ 其他选项 按钮消失", () => {
    render(
      <QuestionConfigurator
        value={[
          {
            question_text: "测试题",
            question_type: "multiselect",
            options: ["选项A", "其他（请说明）"],
            is_required: false,
          },
        ]}
        onChange={vi.fn()}
      />,
    );
    expect(screen.queryByText("+ 其他选项")).not.toBeInTheDocument();
  });
});
