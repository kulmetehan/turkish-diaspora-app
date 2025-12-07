/**
 * Command Palette Configuration
 * 
 * Defines commands and actions available in the command palette (Cmd+K)
 */

import { allNavItems, type NavItem } from "./navigation";

export interface CommandItem {
  id: string;
  label: string;
  keywords: string[];
  icon?: string;
  path?: string;
  action?: () => void;
  group: string;
}

/**
 * Get all commands for the command palette
 */
export function getAllCommands(): CommandItem[] {
  const commands: CommandItem[] = [];
  
  // Add navigation items as commands
  allNavItems.forEach((item) => {
    commands.push({
      id: `nav-${item.id}`,
      label: item.label,
      keywords: [
        item.label.toLowerCase(),
        ...item.path.split("/").filter(Boolean),
        item.icon.toLowerCase(),
      ],
      icon: item.icon,
      path: item.path,
      group: "Navigation",
    });
  });
  
  return commands;
}

/**
 * Filter commands based on search query
 */
export function searchCommands(query: string, commands: CommandItem[]): CommandItem[] {
  if (!query.trim()) {
    return commands;
  }
  
  const lowerQuery = query.toLowerCase();
  
  return commands.filter((cmd) => {
    // Check label match
    if (cmd.label.toLowerCase().includes(lowerQuery)) {
      return true;
    }
    
    // Check keyword matches
    return cmd.keywords.some((keyword) => keyword.includes(lowerQuery));
  });
}

/**
 * Group commands by their group property
 */
export function groupCommands(commands: CommandItem[]): Map<string, CommandItem[]> {
  const grouped = new Map<string, CommandItem[]>();
  
  commands.forEach((cmd) => {
    const existing = grouped.get(cmd.group) || [];
    existing.push(cmd);
    grouped.set(cmd.group, existing);
  });
  
  return grouped;
}









