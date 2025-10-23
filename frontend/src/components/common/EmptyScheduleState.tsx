import { Calendar } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

interface EmptyScheduleStateProps {
  isLoading?: boolean;
}

export function EmptyScheduleState({
  isLoading = false,
}: EmptyScheduleStateProps) {
  if (isLoading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center text-muted-foreground py-12">
            <div className="mx-auto h-12 w-12 mb-4 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            <p className="text-lg font-medium"> Generating Schedule...</p>
            <p className="text-sm mt-2"> This may take a few moments </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="text-center text-muted-foreground py-12">
          <Calendar className="mx-auto h-12 w-12 mb-4 opacity-50" />
          <p className="text-lg font-medium"> No Schedule Generated </p>
          <p className="text-sm mt-2">
            {" "}
            Use the sidebar to upload data and generate a schedule{" "}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
