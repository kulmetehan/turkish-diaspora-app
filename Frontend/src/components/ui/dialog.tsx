import { cn } from "@/lib/ui/cn";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { VisuallyHidden } from "@radix-ui/react-visually-hidden";
import { X } from "lucide-react";
import * as React from "react";

export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;

export const DialogTitle = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Title>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Title
    ref={ref}
    className={cn("text-lg font-semibold leading-none tracking-tight", className)}
    {...props}
  />
));
DialogTitle.displayName = DialogPrimitive.Title.displayName;

export const DialogDescription = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Description>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Description
    ref={ref}
    className={cn("text-sm text-muted-foreground", className)}
    {...props}
  />
));
DialogDescription.displayName = DialogPrimitive.Description.displayName;

function hasDialogTitle(children: React.ReactNode): boolean {
  return React.Children.toArray(children).some((child) => {
    if (!React.isValidElement(child)) return false;
    if (child.type === DialogPrimitive.Title || child.type === DialogTitle) {
      return true;
    }
    if (child.props?.children) {
      return hasDialogTitle(child.props.children);
    }
    return false;
  });
}

export function DialogContent({
  className,
  children,
  ...props
}: React.ComponentProps<typeof DialogPrimitive.Content>) {
  const fallbackTitleId = React.useId();
  const childHasTitle = hasDialogTitle(children);

  const contentProps = {
    ...props,
  } as React.ComponentProps<typeof DialogPrimitive.Content> & { [key: string]: unknown };

  if (!childHasTitle && contentProps["aria-labelledby"] === undefined && contentProps["aria-label"] === undefined) {
    contentProps["aria-labelledby"] = fallbackTitleId;
  }

  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 bg-black/40 animate-fade-in pointer-events-none data-[state=open]:pointer-events-auto data-[state=closed]:hidden z-50" />
      <DialogPrimitive.Content
        className={cn(
          "fixed left-1/2 top-1/2 w-full max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-lg border bg-background p-6 shadow-card z-50",
          "focus:outline-none pointer-events-none data-[state=open]:pointer-events-auto data-[state=closed]:hidden",
          className
        )}
        {...contentProps}
      >
        {!childHasTitle && contentProps["aria-labelledby"] === fallbackTitleId && (
          <VisuallyHidden asChild>
            <DialogPrimitive.Title id={fallbackTitleId}>Dialog</DialogPrimitive.Title>
          </VisuallyHidden>
        )}
        {children}
        <DialogPrimitive.Close className="absolute right-3 top-3 rounded-sm opacity-70 transition-opacity hover:opacity-100 focus:outline-none">
          <X className="h-5 w-5" aria-label="Close" />
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

export function DialogHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("flex flex-col space-y-1.5", className)} {...props} />
  );
}

export function DialogFooter({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2 mt-6", className)} {...props} />
  );
}
