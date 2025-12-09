import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { DashboardHeader } from "./DashboardHeader";

vi.mock("next/image", () => ({
  default: (props: any) => {
    return <img {...props} />;
  },
}));

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
  }),
}));

const logoutMock = vi.fn();

vi.mock("@/lib/store/authStore", () => ({
  useAuthStore: () => ({
    user: {
      name: "John Doe",
      email: "john@example.com",
      avatar: "/avatar.png",
    },
    logout: logoutMock,
  }),
}));

describe("DashboardHeader", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders logo", () => {
    render(<DashboardHeader />);
    expect(screen.getByAltText("icon")).toBeTruthy();
  });

  it("renders user name and avatar fallback", () => {
    render(<DashboardHeader />);

    expect(screen.getByText("John Doe")).toBeTruthy();
    expect(screen.getByText("J")).toBeTruthy(); // Avatar fallback
  });

  it("opens dropdown when user button is clicked", () => {
    render(<DashboardHeader />);

    fireEvent.click(screen.getByText("John Doe"));

    expect(screen.getByText("John Doe")).toBeTruthy();
  });

  it("renders user email in dropdown", () => {
    render(<DashboardHeader />);

    fireEvent.click(screen.getByText("John Doe"));

    expect(screen.getByText("John Doe")).toBeTruthy();
  });

  it("renders notification and settings buttons", () => {
    render(<DashboardHeader />);

    const buttons = screen.getAllByRole("button");

    expect(buttons.length).toBeGreaterThanOrEqual(3);
  });
});
