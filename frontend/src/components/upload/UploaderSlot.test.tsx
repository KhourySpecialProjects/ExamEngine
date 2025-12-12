// src/components/upload/file-upload-slot.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { UploaderSlot } from "./UploaderSlot";
import type { FileUploadSlotProps } from "@/lib/types/upload.types";

describe("UploaderSlot component", () => {
  const mockFile = new File(["test"], "test.csv", { type: "text/csv" });

  const defaultProps: FileUploadSlotProps = {
    slot: {
        label: "Test Slot",
        description: "Upload your CSV",
        id: "courses",
        file: null
    },
    onFileSelect: vi.fn(),
    onRemove: vi.fn(),
    disabled: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });


  it("renders file info and badges when a file is uploaded", () => {
    const props: FileUploadSlotProps = {
      ...defaultProps,
      slot: {
        ...defaultProps.slot,
        file: { file: mockFile, status: "success", rowCount: 10 },
      },
    };
    render(<UploaderSlot {...props} />);

    expect(screen.getByText("test.csv")).toBeDefined();
    expect(screen.getByText("10 rows")).toBeDefined();
    expect(screen.getByText("Uploaded")).toBeDefined();

    // Remove button should exist
    expect(screen.getByRole("button")).toBeDefined();
  });

  it("calls onRemove when remove button is clicked", () => {
    const props: FileUploadSlotProps = {
      ...defaultProps,
      slot: {
        ...defaultProps.slot,
        file: { file: mockFile, status: "success" },
      },
    };
    render(<UploaderSlot {...props} />);

    const removeButton = screen.getByRole("button");
    fireEvent.click(removeButton);
    expect(defaultProps.onRemove).toHaveBeenCalled();
  });

  it("does not render remove button when disabled", () => {
    const props: FileUploadSlotProps = {
      ...defaultProps,
      disabled: true,
      slot: {
        ...defaultProps.slot,
        file: { file: mockFile, status: "success" },
      },
    };
    render(<UploaderSlot {...props} />);
    expect(screen.queryByRole("button")).toBeDefined();
  });

  it("renders error badge and message", () => {
    const props: FileUploadSlotProps = {
      ...defaultProps,
      slot: {
        ...defaultProps.slot,
        file: { file: mockFile, status: "error", error: "Upload failed" },
      },
    };
    render(<UploaderSlot {...props} />);

    expect(screen.getByText("Failed")).toBeDefined();
    expect(screen.getByText("Upload failed")).toBeDefined();
  });
});
