"use client";

import { ChevronsUpDown } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { ButtonGroup } from "@/components/ui/button-group";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { useDatasetStore } from "@/lib/store/datasetStore";
import { DeleteAlert } from "./DeleteAlert";

export function DatasetBar() {
  const {
    datasets,
    selectDataset,
    fetchDatasets,
    getSelectedDataset,
    isLoading,
  } = useDatasetStore();

  const selectedDataset = getSelectedDataset();
  const [open, setOpen] = useState(false);
  useEffect(() => {
    // Fetch datasets on mount
    if (datasets.length === 0) {
      fetchDatasets();
    }
  }, [fetchDatasets, datasets.length]);

  return (
    <div className="pb-4">
      <ButtonGroup className="w-full pr-9">
        {isLoading && datasets.length === 0 ? (
          <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                role="combobox"
                aria-expanded={open}
                className="justify-between w-full"
                disabled
              >
                Loading datasets...
                <ChevronsUpDown className="opacity-50" />
              </Button>
            </PopoverTrigger>
          </Popover>
        ) : datasets.length === 0 ? (
          <Button variant="outline" className="w-full" disabled>
            No datasets
          </Button>
        ) : (
          <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                role="combobox"
                aria-expanded={open}
                className="justify-between w-full"
              >
                {selectedDataset?.dataset_name || "Choose Dataset"}
                <ChevronsUpDown className="opacity-50" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="ml-6 p-0">
              <Command>
                <CommandInput placeholder="Search datasets..." />
                <CommandList>
                  <CommandEmpty>No dataset found.</CommandEmpty>
                  <CommandGroup>
                    {datasets.map((dataset) => (
                      <CommandItem
                        key={dataset.dataset_id}
                        value={dataset.dataset_name}
                        onSelect={() => {
                          selectDataset(dataset.dataset_id);
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
        )}
        <DeleteAlert />
      </ButtonGroup>
    </div>
  );
}
