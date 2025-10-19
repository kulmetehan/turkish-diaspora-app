import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "@/lib/ui/cn";

export const Tabs = TabsPrimitive.Root;

export function TabsList(props: React.ComponentProps<typeof TabsPrimitive.List>) {
  const { className, ...rest } = props;
  return (
    <TabsPrimitive.List
      className={cn("inline-flex h-10 items-center justify-center rounded-md bg-muted p-1 text-muted-foreground", className)}
      {...rest}
    />
  );
}
export function TabsTrigger(props: React.ComponentProps<typeof TabsPrimitive.Trigger>) {
  const { className, ...rest } = props;
  return (
    <TabsPrimitive.Trigger
      className={cn(
        "inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium",
        "data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-soft transition-all",
        className
      )}
      {...rest}
    />
  );
}
export const TabsContent = TabsPrimitive.Content;
