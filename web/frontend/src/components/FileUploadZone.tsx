import { useState } from "react";
import { Upload } from "lucide-react";

type FileUploadZoneProps = {
  file: File | null;
  onFileChange: (file: File | null) => void;
  accept?: string;
  idleLabel?: string;
};

export function FileUploadZone({
  file,
  onFileChange,
  accept = ".pdf,.docx,.txt",
  idleLabel = "Sleep bestand hierheen",
}: FileUploadZoneProps) {
  const [drag, setDrag] = useState(false);

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDrag(false);
    const f = e.dataTransfer.files[0];
    if (f) onFileChange(f);
  };

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDrag(true);
      }}
      onDragLeave={() => setDrag(false)}
      onDrop={onDrop}
      className={`border-2 border-dashed rounded-lg p-10 text-center transition-colors ${
        drag ? "border-primary bg-primary/5" : "border-border"
      }`}
    >
      <Upload className="h-10 w-10 mx-auto text-muted-foreground mb-2" />
      {file ? (
        <p className="font-medium">{file.name}</p>
      ) : (
        <p className="text-muted-foreground">{idleLabel}</p>
      )}
      <input
        type="file"
        accept={accept}
        className="mt-3 text-sm"
        onChange={(e) => onFileChange(e.target.files?.[0] || null)}
      />
    </div>
  );
}
