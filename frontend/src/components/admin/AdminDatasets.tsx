"use client";

import { Download, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { AdminDataset } from "@/lib/api/admin";
import { apiClient } from "@/lib/api/client";
import { downloadBlob } from "@/lib/utils";

export function AdminDatasets() {
  const [datasets, setDatasets] = useState<AdminDataset[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  useEffect(() => {
    apiClient.admin
      .getAllDatasets()
      .then(setDatasets)
      .catch((error) => {
        setLoadError(error instanceof Error ? error.message : "Unknown error");
      })
      .finally(() => setIsLoading(false));
  }, []);

  const handleDownload = async (dataset: AdminDataset) => {
    setDownloadingId(dataset.dataset_id);
    try {
      const zip = await apiClient.admin.downloadDataset(dataset.dataset_id);
      downloadBlob(zip, `${dataset.dataset_name}.zip`);
    } catch (error) {
      toast.error(`Failed to download ${dataset.dataset_name}`, {
        description: error instanceof Error ? error.message : undefined,
      });
    } finally {
      setDownloadingId(null);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (loadError) {
    return (
      <p className="text-sm text-destructive text-center py-12">
        Failed to load datasets: {loadError}
      </p>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>All Datasets</CardTitle>
        <CardDescription>
          Every dataset in the system, across all users ({datasets.length})
        </CardDescription>
      </CardHeader>
      <CardContent>
        {datasets.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">
            No datasets
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Owner</TableHead>
                <TableHead>Uploaded</TableHead>
                <TableHead>Files</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {datasets.map((dataset) => (
                <TableRow key={dataset.dataset_id}>
                  <TableCell className="font-medium">
                    {dataset.dataset_name}
                  </TableCell>
                  <TableCell>
                    <div>{dataset.owner_name}</div>
                    <div className="text-xs text-muted-foreground">
                      {dataset.owner_email}
                    </div>
                  </TableCell>
                  <TableCell>
                    {new Date(dataset.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {dataset.file_types.map((type) => (
                        <Badge key={type} variant="secondary">
                          {type}
                        </Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleDownload(dataset)}
                      disabled={downloadingId !== null}
                    >
                      {downloadingId === dataset.dataset_id ? (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      ) : (
                        <Download className="mr-2 h-4 w-4" />
                      )}
                      Download
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
