import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Icon } from "@/components/Icon";
import {
  listOutreachContacts,
  deleteOutreachContact,
  bulkDeleteOutreachContacts,
  listLocationsWithoutContact,
  queueOutreachEmail,
  sendQueuedOutreachEmails,
  listOutreachEmails,
  type AdminContactResponse,
  type LocationWithoutContact,
  type OutreachEmailResponse,
} from "@/lib/apiAdmin";
import { toast } from "sonner";
import AddContactDialog from "./AddContactDialog";

type FilterMode = "with_email" | "without_email";

export default function OutreachContactsList() {
  const [filterMode, setFilterMode] = useState<FilterMode>("with_email");
  const [contacts, setContacts] = useState<AdminContactResponse[]>([]);
  const [locationsWithoutContact, setLocationsWithoutContact] = useState<LocationWithoutContact[]>([]);
  const [locationsWithoutContactTotal, setLocationsWithoutContactTotal] = useState(0);
  const [locationsWithoutContactOffset, setLocationsWithoutContactOffset] = useState(0);
  const [locationsWithoutContactLimit] = useState(100); // Items per page
  const [loading, setLoading] = useState(false);
  const [locationIdFilter, setLocationIdFilter] = useState<string>("");
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [selectedLocationForAdd, setSelectedLocationForAdd] = useState<LocationWithoutContact | null>(null);
  const [selectedContactIds, setSelectedContactIds] = useState<Set<number>>(new Set());
  const [emailStatuses, setEmailStatuses] = useState<Map<number, OutreachEmailResponse>>(new Map());
  const [sending, setSending] = useState(false);

  const loadContacts = async () => {
    setLoading(true);
    try {
      const params: { location_id?: number; limit?: number; offset?: number } = {
        limit: 500,
        offset: 0,
      };
      if (locationIdFilter.trim()) {
        const id = parseInt(locationIdFilter.trim(), 10);
        if (!isNaN(id)) {
          params.location_id = id;
        }
      }
      const data = await listOutreachContacts(params);
      setContacts(data);
    } catch (error: any) {
      toast.error(`Failed to load contacts: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const loadLocationsWithoutContact = async (offset: number = 0) => {
    setLoading(true);
    try {
      const data = await listLocationsWithoutContact({
        limit: locationsWithoutContactLimit,
        offset: offset,
      });
      setLocationsWithoutContact(data.items);
      setLocationsWithoutContactTotal(data.total);
      setLocationsWithoutContactOffset(offset);
    } catch (error: any) {
      toast.error(`Failed to load locations: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Load data when filter mode changes
  useEffect(() => {
    if (filterMode === "with_email") {
      loadContacts();
    } else {
      setLocationsWithoutContactOffset(0); // Reset to first page
      loadLocationsWithoutContact(0);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterMode]);

  // Reload contacts when locationIdFilter changes (only for with_email mode)
  useEffect(() => {
    if (filterMode === "with_email") {
      loadContacts();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locationIdFilter]);

  // Load email statuses on mount and when contacts change
  useEffect(() => {
    if (filterMode === "with_email") {
      loadEmailStatuses();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterMode, contacts]);

  const handleDelete = async (contactId: number) => {
    if (!confirm("Are you sure you want to delete this contact?")) {
      return;
    }

    try {
      await deleteOutreachContact(contactId);
      toast.success("Contact deleted successfully");
      loadContacts();
    } catch (error: any) {
      toast.error(`Failed to delete contact: ${error.message}`);
    }
  };

  const handleBulkDelete = async () => {
    if (selectedContactIds.size === 0) {
      return;
    }

    const count = selectedContactIds.size;
    if (!confirm(`Are you sure you want to delete ${count} contact(s)?`)) {
      return;
    }

    try {
      const result = await bulkDeleteOutreachContacts(Array.from(selectedContactIds));
      if (result.failed_count === 0) {
        toast.success(`Successfully deleted ${result.deleted_count} contact(s)`);
      } else {
        toast.warning(`Deleted ${result.deleted_count} contact(s), ${result.failed_count} failed`);
        if (result.errors.length > 0) {
          console.error("Bulk delete errors:", result.errors);
        }
      }
      setSelectedContactIds(new Set());
      loadContacts();
    } catch (error: any) {
      toast.error(`Failed to delete contacts: ${error.message}`);
    }
  };

  const handleToggleSelect = (contactId: number) => {
    const newSelected = new Set(selectedContactIds);
    if (newSelected.has(contactId)) {
      newSelected.delete(contactId);
    } else {
      newSelected.add(contactId);
    }
    setSelectedContactIds(newSelected);
  };

  const handleSelectAll = () => {
    if (selectedContactIds.size === contacts.length) {
      setSelectedContactIds(new Set());
    } else {
      setSelectedContactIds(new Set(contacts.map(c => c.id)));
    }
  };

  const handleAddContactForLocation = (location: LocationWithoutContact) => {
    setSelectedLocationForAdd(location);
    setIsAddDialogOpen(true);
  };

  const handleContactCreated = () => {
    loadContacts();
    loadLocationsWithoutContact();
    setSelectedLocationForAdd(null);
  };

  const loadEmailStatuses = async (locationId?: number) => {
    try {
      const emails = await listOutreachEmails({ 
        location_id: locationId, 
        limit: 500 
      });
      const statusMap = new Map<number, OutreachEmailResponse>();
      emails.forEach(email => {
        statusMap.set(email.location_id, email);
      });
      setEmailStatuses(statusMap);
    } catch (error: any) {
      console.error("Failed to load email statuses:", error);
    }
  };

  const handleQueueEmail = async (locationId: number) => {
    try {
      const result = await queueOutreachEmail(locationId);
      if (result.success) {
        toast.success(result.message);
        // Reload email statuses
        await loadEmailStatuses(locationId);
      }
    } catch (error: any) {
      toast.error(`Failed to queue email: ${error.message}`);
    }
  };

  const handleSendEmails = async () => {
    setSending(true);
    try {
      const result = await sendQueuedOutreachEmails(10);
      if (result.success) {
        toast.success(`Sent ${result.sent} email(s), ${result.failed} failed`);
        if (result.errors.length > 0) {
          console.error("Send errors:", result.errors);
        }
      } else {
        toast.error("Failed to send emails");
      }
      // Reload all email statuses
      await loadEmailStatuses();
    } catch (error: any) {
      toast.error(`Failed to send emails: ${error.message}`);
    } finally {
      setSending(false);
    }
  };

  const getSourceBadge = (source: string) => {
    const badgeColors: Record<string, string> = {
      osm: "bg-blue-50 text-blue-700 border-blue-200",
      website: "bg-green-50 text-green-700 border-green-200",
      google: "bg-purple-50 text-purple-700 border-purple-200",
      social: "bg-pink-50 text-pink-700 border-pink-200",
      manual: "bg-orange-50 text-orange-700 border-orange-200",
    };

    const colorClass = badgeColors[source] || "bg-gray-50 text-gray-700 border-gray-200";

    return (
      <Badge variant="outline" className={colorClass}>
        {source.toUpperCase()}
      </Badge>
    );
  };

  const getConfidenceBadge = (score: number) => {
    let colorClass = "bg-gray-50 text-gray-700 border-gray-200";
    if (score >= 80) {
      colorClass = "bg-green-50 text-green-700 border-green-200";
    } else if (score >= 50) {
      colorClass = "bg-yellow-50 text-yellow-700 border-yellow-200";
    } else {
      colorClass = "bg-red-50 text-red-700 border-red-200";
    }

    return (
      <Badge variant="outline" className={colorClass}>
        {score}
      </Badge>
    );
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("nl-NL", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <>
      <Card>
        <CardContent className="p-6">
          <div className="space-y-4">
            {/* Header and Actions */}
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Outreach Contacts</h2>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" onClick={filterMode === "with_email" ? loadContacts : () => loadLocationsWithoutContact(locationsWithoutContactOffset)}>
                  <Icon name="RefreshCw" sizeRem={1} className="mr-2" />
                  Refresh
                </Button>
                {filterMode === "with_email" && (
                  <>
                    <Button 
                      variant="default" 
                      size="sm" 
                      onClick={handleSendEmails}
                      disabled={sending}
                    >
                      <Icon name="Send" sizeRem={1} className="mr-2" />
                      {sending ? "Sending..." : "Send Queued Emails"}
                    </Button>
                    {selectedContactIds.size > 0 && (
                      <Button 
                        variant="destructive" 
                        size="sm" 
                        onClick={handleBulkDelete}
                      >
                        <Icon name="Trash2" sizeRem={1} className="mr-2" />
                        Delete Selected ({selectedContactIds.size})
                      </Button>
                    )}
                    <Button size="sm" onClick={() => setIsAddDialogOpen(true)}>
                      <Icon name="Plus" sizeRem={1} className="mr-2" />
                      Add Contact
                    </Button>
                  </>
                )}
              </div>
            </div>

            {/* Filter Toggle */}
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <label className="text-sm font-medium">Filter:</label>
                <div className="flex rounded-md border border-input overflow-hidden">
                  <button
                    type="button"
                    onClick={() => setFilterMode("with_email")}
                    className={`px-4 py-2 text-sm font-medium transition-colors ${
                      filterMode === "with_email"
                        ? "bg-primary text-primary-foreground"
                        : "bg-background text-foreground hover:bg-muted"
                    }`}
                  >
                    Met Email ({contacts.length})
                  </button>
                  <button
                    type="button"
                    onClick={() => setFilterMode("without_email")}
                    className={`px-4 py-2 text-sm font-medium transition-colors border-l border-input ${
                      filterMode === "without_email"
                        ? "bg-primary text-primary-foreground"
                        : "bg-background text-foreground hover:bg-muted"
                    }`}
                  >
                    Zonder Email ({locationsWithoutContactTotal})
                  </button>
                </div>
              </div>
              {filterMode === "with_email" && (
                <div className="flex items-center gap-2">
                  <label className="text-sm font-medium">Location ID:</label>
                  <input
                    type="number"
                    value={locationIdFilter}
                    onChange={(e) => setLocationIdFilter(e.target.value)}
                    placeholder="Filter by location ID"
                    className="w-40 rounded-md border border-input bg-background px-3 py-1.5 text-sm"
                  />
                </div>
              )}
            </div>

            {/* Content based on filter mode */}
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="text-muted-foreground">Loading...</div>
              </div>
            ) : filterMode === "with_email" ? (
              /* Contacts with Email */
              contacts.length === 0 ? (
                <div className="flex items-center justify-center py-8">
                  <div className="text-muted-foreground">No contacts found</div>
                </div>
              ) : (
                <div className="space-y-2">
                  {/* Select All Checkbox */}
                  <div className="flex items-center gap-2 pb-2 border-b">
                    <input
                      type="checkbox"
                      checked={selectedContactIds.size === contacts.length && contacts.length > 0}
                      onChange={handleSelectAll}
                      className="w-4 h-4 rounded border-gray-300"
                    />
                    <label className="text-sm font-medium">
                      Select All ({contacts.length})
                    </label>
                  </div>
                  {contacts.map((contact) => (
                    <Card key={contact.id}>
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between gap-3">
                          <input
                            type="checkbox"
                            checked={selectedContactIds.has(contact.id)}
                            onChange={() => handleToggleSelect(contact.id)}
                            className="w-4 h-4 mt-1 rounded border-gray-300"
                          />
                          <div className="flex-1 space-y-2">
                            <div className="flex items-center gap-3">
                              <h3 className="font-semibold">
                                {contact.location_name || `Location ${contact.location_id}`}
                              </h3>
                              {getSourceBadge(contact.source)}
                              {getConfidenceBadge(contact.confidence_score)}
                            </div>
                            <div className="text-sm text-muted-foreground space-y-1">
                              <div>
                                <strong>Email:</strong> {contact.email}
                              </div>
                              <div>
                                <strong>Location ID:</strong> {contact.location_id}
                              </div>
                              <div>
                                <strong>Discovered:</strong> {formatDate(contact.discovered_at)}
                              </div>
                              <div>
                                <strong>Created:</strong> {formatDate(contact.created_at)}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            {(() => {
                              const emailStatus = emailStatuses.get(contact.location_id);
                              if (emailStatus) {
                                const statusColors: Record<string, string> = {
                                  queued: "bg-yellow-50 text-yellow-700 border-yellow-200",
                                  sent: "bg-green-50 text-green-700 border-green-200",
                                  delivered: "bg-green-50 text-green-700 border-green-200",
                                  clicked: "bg-blue-50 text-blue-700 border-blue-200",
                                  bounced: "bg-red-50 text-red-700 border-red-200",
                                  opted_out: "bg-gray-50 text-gray-700 border-gray-200",
                                };
                                const colorClass = statusColors[emailStatus.status] || "bg-gray-50 text-gray-700 border-gray-200";
                                return (
                                  <Badge variant="outline" className={colorClass}>
                                    {emailStatus.status.toUpperCase()}
                                  </Badge>
                                );
                              } else {
                                return (
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => handleQueueEmail(contact.location_id)}
                                  >
                                    <Icon name="Mail" sizeRem={1} className="mr-1" />
                                    Queue Email
                                  </Button>
                                );
                              }
                            })()}
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDelete(contact.id)}
                              className="text-red-600 hover:text-red-700"
                            >
                              <Icon name="Trash2" sizeRem={1} />
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )
            ) : (
              /* Locations without Email */
              locationsWithoutContact.length === 0 ? (
                <div className="flex items-center justify-center py-8">
                  <div className="text-muted-foreground">All verified locations have contacts</div>
                </div>
              ) : (
                <>
                  <div className="space-y-2">
                    {locationsWithoutContact.map((location) => (
                      <Card key={location.id}>
                        <CardContent className="p-4">
                          <div className="flex items-start justify-between">
                            <div className="flex-1 space-y-2">
                              <div className="flex items-center gap-3">
                                <h3 className="font-semibold">
                                  {location.name || `Location ${location.id}`}
                                </h3>
                                {location.category && (
                                  <Badge variant="outline" className="bg-slate-50 text-slate-700 border-slate-200">
                                    {location.category}
                                  </Badge>
                                )}
                              </div>
                              <div className="text-sm text-muted-foreground space-y-1">
                                {location.address && (
                                  <div>
                                    <strong>Address:</strong> {location.address}
                                  </div>
                                )}
                                <div>
                                  <strong>Location ID:</strong> {location.id}
                                </div>
                                <div className="text-xs text-amber-600">
                                  ⚠️ Geen e-mailadres gevonden
                                </div>
                              </div>
                            </div>
                            <Button
                              size="sm"
                              onClick={() => handleAddContactForLocation(location)}
                              className="bg-primary text-primary-foreground hover:bg-primary/90"
                            >
                              <Icon name="Plus" sizeRem={1} className="mr-2" />
                              Toevoegen
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                  
                  {/* Pagination Controls */}
                  {locationsWithoutContactTotal > locationsWithoutContactLimit && (
                    <div className="flex items-center justify-between pt-4 border-t">
                      <div className="text-sm text-muted-foreground">
                        Toont {locationsWithoutContactOffset + 1} - {Math.min(locationsWithoutContactOffset + locationsWithoutContactLimit, locationsWithoutContactTotal)} van {locationsWithoutContactTotal} locaties
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => loadLocationsWithoutContact(Math.max(0, locationsWithoutContactOffset - locationsWithoutContactLimit))}
                          disabled={locationsWithoutContactOffset === 0 || loading}
                        >
                          <Icon name="ChevronLeft" sizeRem={1} className="mr-1" />
                          Vorige
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => loadLocationsWithoutContact(locationsWithoutContactOffset + locationsWithoutContactLimit)}
                          disabled={locationsWithoutContactOffset + locationsWithoutContactLimit >= locationsWithoutContactTotal || loading}
                        >
                          Volgende
                          <Icon name="ChevronRight" sizeRem={1} className="ml-1" />
                        </Button>
                      </div>
                    </div>
                  )}
                </>
              )
            )}
          </div>
        </CardContent>
      </Card>

      <AddContactDialog
        open={isAddDialogOpen}
        onOpenChange={(open) => {
          setIsAddDialogOpen(open);
          if (!open) {
            setSelectedLocationForAdd(null);
          }
        }}
        onCreated={handleContactCreated}
        locationId={selectedLocationForAdd?.id}
        locationName={selectedLocationForAdd?.name || undefined}
      />
    </>
  );
}

