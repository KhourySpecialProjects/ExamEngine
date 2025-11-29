"use client";

import { ChevronsUpDown, Trash } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { useDatasetStore } from "@/lib/store/datasetStore";
import type { DatasetMetadata } from "@/lib/types/datasets.api.types";

export function DeleteDataset() {
  const { datasets, fetchDatasets } = useDatasetStore();
  const [currentDataset, setDataset] = useState<DatasetMetadata | null>();
  const deleteDataset = useDatasetStore((state) => state.deleteDataset);

  const handleDeleteDataset = async () => {
    const uploadToast = toast.loading("Deleting dataset...", {
      description: "Please wait while we delete your dataset",
    });
    if (currentDataset) {
      try {
        const _result = await deleteDataset(currentDataset.dataset_id);
        setDataset(null);
        toast.success("Deletion successful!", {
          id: uploadToast,
          description: `${currentDataset.dataset_name} deleted successfully!`,
        });
      } catch (_error) {
        toast.error(`Could not delete ${currentDataset.dataset_name}`);
      }
    }
  };

  useEffect(() => {
    if (datasets.length === 0) {
      fetchDatasets();
    }
  }, [fetchDatasets, datasets.length]);
  const [open, setOpen] = useState(false);
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button className="w-full text-red-400">
          <Trash className="h-4" />
          Delete Datasets
        </Button>
      </DialogTrigger>

      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Delete Datasets</DialogTitle>
          <DialogDescription>Irreversible</DialogDescription>
        </DialogHeader>

        <div className="space-y-2 py-4">
          <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                role="combobox"
                aria-expanded={open}
                className="w-[200px] justify-between"
              >
                {currentDataset?.dataset_name || "Choose Dataset"}
                <ChevronsUpDown className="opacity-50" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[200px] p-0">
              <Command>
                <CommandInput
                  placeholder="Search framework..."
                  className="h-9"
                />
                <CommandList>
                  <CommandEmpty>No framework found.</CommandEmpty>
                  <CommandGroup>
                    {datasets.map((dataset) => (
                      <CommandItem
                        key={dataset.dataset_id}
                        value={dataset.dataset_name}
                        onSelect={(value) => {
                          const selected = datasets.find(
                            (d) => d.dataset_name === value,
                          );
                          setDataset(
                            currentDataset?.dataset_id === selected?.dataset_id
                              ? undefined
                              : selected,
                          );
                          setOpen(false);
                        }}
                      >
                        {dataset.dataset_name}
                      </CommandItem>
                    ))}
                  </CommandGroup>
                </CommandList>
              </Command>
            </PopoverContent>
          </Popover>
          <div>
            <Button className="text-red-400" onClick={handleDeleteDataset}>
              Delete dataset
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
