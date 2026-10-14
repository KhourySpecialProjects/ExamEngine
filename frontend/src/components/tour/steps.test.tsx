import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DashboardHeader } from "@/components/layouts/DashboardHeader";
import { steps } from "./steps";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("onborda", () => ({ useOnborda: () => ({ startOnborda: vi.fn() }) }));
vi.mock("@/lib/store/authStore", () => ({
  useAuthStore: () => ({ user: null, logout: vi.fn() }),
}));

describe("tour steps", () => {
  const tour = steps[0].steps;

  it("ends on the header's Docs link", () => {
    expect(tour).toHaveLength(6);
    const last = tour[tour.length - 1];
    expect(last.title).toBe("Read the docs");
    expect(last.selector).toBe("#docs-id");

    const { container } = render(<DashboardHeader />);
    expect(container.querySelector(last.selector)?.getAttribute("href")).toBe(
      "/docs",
    );
  });
});
