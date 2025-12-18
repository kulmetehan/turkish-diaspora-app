import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Command } from "cmdk";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Icon } from "@/components/Icon";
import { cn } from "@/lib/ui/cn";
import { getAllCommands, searchCommands, groupCommands, type CommandItem } from "@/lib/admin/command-palette";

interface AdminCommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function AdminCommandPalette({ open, onOpenChange }: AdminCommandPaletteProps) {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [commands, setCommands] = useState<CommandItem[]>([]);
  
  useEffect(() => {
    setCommands(getAllCommands());
  }, []);
  
  const filteredCommands = searchCommands(search, commands);
  const groupedCommands = groupCommands(filteredCommands);
  
  const handleSelect = (command: CommandItem) => {
    if (command.path) {
      navigate(command.path);
      onOpenChange(false);
      setSearch("");
    } else if (command.action) {
      command.action();
      onOpenChange(false);
      setSearch("");
    }
  };
  
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl p-0 overflow-hidden">
        <Command className="rounded-lg border-none" shouldFilter={false}>
          <div className="flex items-center border-b px-4">
            <Icon name="Search" sizeRem={1} className="mr-2 text-muted-foreground" />
            <Command.Input
              placeholder="Search pages and commands..."
              value={search}
              onValueChange={setSearch}
              className={cn(
                "flex h-12 w-full rounded-md bg-transparent py-3 text-sm outline-none",
                "placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
              )}
            />
          </div>
          <Command.List className="max-h-[400px] overflow-y-auto p-2">
            <Command.Empty className="py-6 text-center text-sm text-muted-foreground">
              No results found.
            </Command.Empty>
            
            {Array.from(groupedCommands.entries()).map(([group, items]) => (
              <Command.Group
                key={group}
                heading={group}
                className="px-2 py-1.5 text-xs font-semibold text-muted-foreground"
              >
                {items.map((cmd) => (
                  <Command.Item
                    key={cmd.id}
                    value={cmd.id}
                    onSelect={() => handleSelect(cmd)}
                    className={cn(
                      "flex items-center gap-3 rounded-md px-3 py-2 text-sm",
                      "cursor-pointer select-none outline-none",
                      "aria-selected:bg-accent aria-selected:text-accent-foreground"
                    )}
                  >
                    {cmd.icon && (
                      <Icon
                        name={cmd.icon as any}
                        sizeRem={1.25}
                        className="text-muted-foreground"
                      />
                    )}
                    <span>{cmd.label}</span>
                    {cmd.path && (
                      <kbd className="ml-auto pointer-events-none flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground opacity-100">
                        <span className="text-xs">⌘</span>K
                      </kbd>
                    )}
                  </Command.Item>
                ))}
              </Command.Group>
            ))}
          </Command.List>
        </Command>
      </DialogContent>
    </Dialog>
  );
}























