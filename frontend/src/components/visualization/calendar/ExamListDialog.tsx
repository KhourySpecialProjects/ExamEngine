import {
  Dialog,
  DialogContent,
  DialogDescription,
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
      <DialogContent className="max-w-3xl max-h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold">
            {selectedCell?.day} - {selectedCell?.timeSlot}
          </DialogTitle>
          <DialogDescription className="flex items-center gap-4 text-sm pt-2 font-semibold text-foreground">
            {selectedCell?.examCount || 0} exams scheduled
          </DialogDescription>
        </DialogHeader>

        <Separator />

        <div className="flex-1 overflow-auto no-scrollbar">
          <ExamList exams={selectedCell?.exams || []} />
        </div>
      </DialogContent>
    </Dialog>
  );
}
