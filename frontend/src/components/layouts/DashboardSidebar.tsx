"use client";

import {
	Building,
	Calendar,
	Database,
	SlidersHorizontal,
	Users,
} from "lucide-react";
import { useEffect } from "react";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { useDatasetStore } from "@/lib/store/datasetStore";
import { getTimeAgo } from "@/lib/utils";
import { DeleteDataset } from "../dataset/DeleteDataset";
import { ScheduleRunner } from "../schedule/ScheduleRunner";
import { Uploader } from "../upload/Uploader";

export function DashboardSidebar() {
	const {
		datasets,
		selectedDatasetId,
		selectDataset,
		fetchDatasets,
		getSelectedDataset,
		isLoading,
	} = useDatasetStore();

	const selectedDataset = getSelectedDataset();

	useEffect(() => {
		// Fetch datasets on mount
		if (datasets.length === 0) {
			fetchDatasets();
		}
	}, [fetchDatasets, datasets.length]);

	const handleValueChange = (value: string) => {
		selectDataset(value);
	};

	return (
		<div className="p-6 space-y-6">
			<section>
				<div className="flex items-center gap-2 mb-3">
					<Database className="text-green-800" />
					<h2 className="font-semibold text-sm">Data Management</h2>
				</div>

				{/* Dataset Selector */}
				{isLoading && datasets.length === 0 ? (
					<Select disabled>
						<SelectTrigger className="mb-3 w-full">
							<SelectValue placeholder="Loading datasets..." />
						</SelectTrigger>
					</Select>
				) : datasets.length === 0 ? (
					<Select disabled>
						<SelectTrigger className="mb-3 w-full">
							<SelectValue placeholder="No datasets - Upload one" />
						</SelectTrigger>
					</Select>
				) : (
					<Select
						value={selectedDatasetId || undefined}
						onValueChange={handleValueChange}
					>
						<SelectTrigger className="mb-3 w-full">
							<SelectValue placeholder="Select dataset">
								{selectedDataset && (
									<span className="truncate">
										{selectedDataset.dataset_name}
									</span>
								)}
							</SelectValue>
						</SelectTrigger>
						<SelectContent>
							{datasets.map((dataset) => (
								<SelectItem key={dataset.dataset_id} value={dataset.dataset_id}>
									<div className="flex flex-col">
										<div className="flex items-center gap-2">
											<span className="font-medium">
												{dataset.dataset_name}
											</span>
										</div>
										<span className="text-xs text-muted-foreground">
											{dataset.files.courses.unique_crns} courses •
											{dataset.files.enrollments.unique_students} students
										</span>
									</div>
								</SelectItem>
							))}
						</SelectContent>
					</Select>
				)}

				{/* Upload Button */}
				<Uploader />

				{/*Delte Dataset Button*/}
				<div className="pt-3">
					<DeleteDataset />
				</div>
				{/* Dataset Info */}
				{selectedDataset ? (
					<div className="mt-3 text-sm space-y-2">
						<div className="font-medium text-foreground">Current Dataset</div>

						<div className="space-y-1 text-muted-foreground">
							<div className="flex items-center gap-2">
								<Database className="h-3.5 w-3.5" />
								<span>{selectedDataset.files.courses.unique_crns} courses</span>
							</div>

							<div className="flex items-center gap-2">
								<Users className="h-3.5 w-3.5" />
								<span>
									{selectedDataset.files.enrollments.unique_students} students
								</span>
							</div>

							<div className="flex items-center gap-2">
								<Building className="h-3.5 w-3.5" />
								<span>{selectedDataset.files.rooms.unique_rooms} rooms</span>
							</div>

							<div className="flex items-center gap-2">
								<Calendar className="h-3.5 w-3.5" />
								<span>Updated: {getTimeAgo(selectedDataset.created_at)}</span>
							</div>
						</div>
					</div>
				) : (
					<div className="mt-3 text-sm text-muted-foreground text-center py-4">
						{datasets.length === 0 ? (
							<span>Upload a dataset to get started</span>
						) : (
							<span>Select a dataset above</span>
						)}
					</div>
				)}
			</section>

			<section>
				<div className="flex items-center gap-2 mb-3">
					<SlidersHorizontal />
					<h2 className="font-semibold text-sm">Optimization Controls</h2>
				</div>
				<ScheduleRunner />
			</section>
		</div>
	);
}
