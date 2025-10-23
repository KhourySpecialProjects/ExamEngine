import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { useCalendarStore } from "@/lib/store/calendarStore";
import { ExamList } from "./ExamList";

export function ExamListDialog() {
  const { selectedCell, selectCell } = useCalendarStore();

  if (!selectedCell) return null;

  return (
    <Dialog open={!!selectedCell} onOpenChange={() => selectCell(null)}>
      <DialogContent className="max-w-3xl max-h-[85vh] flex flex-col gap-4">
        <DialogHeader>
          {/* Time slot details */}
          <DialogTitle className="flex items-center gap-2">
            {selectedCell.day} - {selectedCell.timeSlot}
          </DialogTitle>
          Some details about time slot goes here e.g how many exams, how many
          conflicts
        </DialogHeader>
        <Separator />
        <ExamList exams={selectedCell.exams} />
      </DialogContent>
    </Dialog>
  );
}
