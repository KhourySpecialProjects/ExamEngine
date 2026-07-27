import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ChangePasswordForm } from "./ChangePasswordForm";

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

vi.mock("@/lib/api/client", () => ({
  apiClient: { auth: { changePassword: vi.fn() } },
}));

import { toast } from "sonner";
import { apiClient } from "@/lib/api/client";

const changePassword = vi.mocked(apiClient.auth.changePassword);

function fill(current: string, next: string, confirm: string) {
  fireEvent.change(screen.getByLabelText("Current Password"), {
    target: { value: current },
  });
  fireEvent.change(screen.getByLabelText("New Password"), {
    target: { value: next },
  });
  fireEvent.change(screen.getByLabelText("Confirm New Password"), {
    target: { value: confirm },
  });
}

function submit() {
  fireEvent.click(screen.getByRole("button", { name: "Update Password" }));
}

describe("ChangePasswordForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("blocks a weak new password without calling the API", () => {
    render(<ChangePasswordForm />);
    fill("oldpass", "abcdefgh", "abcdefgh");
    submit();

    expect(toast.error).toHaveBeenCalledWith(
      "New password must include at least one number.",
    );
    expect(changePassword).not.toHaveBeenCalled();
  });

  it("blocks mismatched confirmation without calling the API", () => {
    render(<ChangePasswordForm />);
    fill("oldpass", "password1!", "password1?");
    submit();

    expect(toast.error).toHaveBeenCalledWith(
      "New password and confirmation do not match.",
    );
    expect(changePassword).not.toHaveBeenCalled();
  });

  it("submits valid input and shows a success toast", async () => {
    changePassword.mockResolvedValue({
      message: "Password updated successfully",
    });
    render(<ChangePasswordForm />);
    fill("oldpass", "password1!", "password1!");
    submit();

    await waitFor(() => {
      expect(changePassword).toHaveBeenCalledTimes(1);
    });
    expect(changePassword).toHaveBeenCalledWith("oldpass", "password1!");
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith(
        "Password updated successfully",
      );
    });
  });

  it("surfaces the backend error in an error toast", async () => {
    changePassword.mockRejectedValue(
      new Error("Current password is incorrect"),
    );
    render(<ChangePasswordForm />);
    fill("oldpass", "password1!", "password1!");
    submit();

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("Failed to update password", {
        description: "Current password is incorrect",
      });
    });
  });
});
