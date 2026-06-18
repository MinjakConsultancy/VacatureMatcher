import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { FileUploadZone } from "./FileUploadZone";

describe("FileUploadZone", () => {
  it("renders idle label when no file", () => {
    render(<FileUploadZone file={null} onFileChange={() => {}} idleLabel="Kies een CV" />);
    expect(screen.getByText("Kies een CV")).toBeInTheDocument();
  });

  it("shows filename after file input change", () => {
    const onFileChange = vi.fn();
    const { container } = render(<FileUploadZone file={null} onFileChange={onFileChange} />);

    const file = new File(["cv"], "mijn-cv.txt", { type: "text/plain" });
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    expect(onFileChange).toHaveBeenCalledWith(file);
  });

  it("calls onFileChange on drop", () => {
    const onFileChange = vi.fn();
    const { container } = render(<FileUploadZone file={null} onFileChange={onFileChange} />);

    const file = new File(["cv"], "drop-cv.txt", { type: "text/plain" });
    const zone = container.firstElementChild as HTMLElement;
    fireEvent.drop(zone, { dataTransfer: { files: [file] } });

    expect(onFileChange).toHaveBeenCalledWith(file);
  });
});
