// src/components/upload/file-upload-slot.tsx
"use client";

import {
  AlertCircle,
  CheckCircle2,
  FileSpreadsheet,
  Loader2,
  Upload,
  X,
} from "lucide-react";
import { useRef } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { FileUploadSlotProps } from "@/types/upload.types";

export function UploaderSlot({
  slot,
  onFileSelect,
  onRemove,
  disabled,
}: FileUploadSlotProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleClick = () => {
    if (!disabled && !slot.file) {
      fileInputRef.current?.click();
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) onFileSelect(file);
  };

  const getStatusIcon = () => {
    if (!slot.file) return null;

    const icons = {
      uploading: <Loader2 className="h-5 w-5 text-blue-600 animate-spin" />,
      success: <CheckCircle2 className="h-5 w-5 text-green-600" />,
      error: <AlertCircle className="h-5 w-5 text-red-600" />,
      pending: <FileSpreadsheet className="h-5 w-5 text-gray-600" />,
    };

    return icons[slot.file.status];
  };

  const getStatusBadge = () => {
    if (!slot.file) return null;

    const badges = {
      uploading: (
        <Badge variant="outline" className="bg-blue-50">
          Uploading...
        </Badge>
      ),
      success: (
        <Badge variant="outline" className="bg-green-50 text-green-700">
          Uploaded
        </Badge>
      ),
      error: <Badge variant="destructive">Failed</Badge>,
      pending: <Badge variant="outline">Ready</Badge>,
    };

    return badges[slot.file.status];
  };

  const isClickable = !disabled && !slot.file;

  return (
    <div
      className={`
        relative border-2 border-dashed rounded-lg p-4 transition-all
        ${slot.file ? "border-primary bg-primary/5" : "border-border hover:border-primary/50 hover:bg-accent/50"}
        ${disabled ? "opacity-50 cursor-not-allowed" : isClickable ? "cursor-pointer" : ""}
      `}
      onClick={handleClick}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv"
        onChange={handleFileChange}
        className="hidden"
        disabled={disabled || !!slot.file}
      />

      <div className="flex items-center gap-3">
        <div className="flex-shrink-0">{getStatusIcon()}</div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="font-medium text-sm">{slot.label}</h4>
            {getStatusBadge()}
          </div>

          {slot.file ? (
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground truncate">
                {slot.file.file.name}
              </p>
              {slot.file.rowCount && (
                <p className="text-xs text-muted-foreground">
                  {slot.file.rowCount} rows
                </p>
              )}
              {slot.file.error && (
                <p className="text-xs text-red-600">{slot.file.error}</p>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">{slot.description}</p>
          )}
        </div>

        {slot.file && !disabled ? (
          <Button
            variant="ghost"
            size="icon"
            onClick={(e) => {
              e.stopPropagation();
              onRemove();
            }}
            className="flex-shrink-0"
          >
            <X className="h-4 w-4" />
          </Button>
        ) : !slot.file && !disabled ? (
          <div className="flex-shrink-0">
            <Upload className="h-5 w-5 text-muted-foreground" />
          </div>
        ) : null}
      </div>
    </div>
  );
}
