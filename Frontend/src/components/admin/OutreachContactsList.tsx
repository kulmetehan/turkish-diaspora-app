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
  bulkQueueOutreachEmails,
  sendQueuedOutreachEmails,
  listOutreachEmails,
  getCities,
  listAdminLocationCategories,
  type AdminContactResponse,
  type LocationWithoutContact,
  type OutreachEmailResponse,
  type CityInfo,
} from "@/lib/apiAdmin";
import type { CategoryOption } from "@/api/fetchLocations";
import { toast } from "sonner";
import AddContactDialog from "./AddContactDialog";

type FilterMode = "with_email" | "without_email" | "queued";
type EmailStatusFilter = "all" | "not_sent" | "sent";

export default function OutreachContactsList() {
  const [filterMode, setFilterMode] = useState<FilterMode>("with_email");
  const [contacts, setContacts] = useState<AdminContactResponse[]>([]);
  const [queuedContacts, setQueuedContacts] = useState<AdminContactResponse[]>([]);
  const [queuedContactsTotal, setQueuedContactsTotal] = useState(0);
  const [locationsWithoutContact, setLocationsWithoutContact] = useState<LocationWithoutContact[]>([]);
  const [locationsWithoutContactTotal, setLocationsWithoutContactTotal] = useState(0);
  const [locationsWithoutContactOffset, setLocationsWithoutContactOffset] = useState(0);
  const [locationsWithoutContactLimit] = useState(100); // Items per page
  const [loading, setLoading] = useState(false);
  const [locationIdFilter, setLocationIdFilter] = useState<string>("");
  const [emailStatusFilter, setEmailStatusFilter] = useState<EmailStatusFilter>("all");
  const [cityFilter, setCityFilter] = useState<string>("");
  const [cities, setCities] = useState<CityInfo[]>([]);
  const [citiesLoading, setCitiesLoading] = useState(false);
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [selectedLocationForAdd, setSelectedLocationForAdd] = useState<LocationWithoutContact | null>(null);
  const [selectedContactIds, setSelectedContactIds] = useState<Set<number>>(new Set());
  const [emailStatuses, setEmailStatuses] = useState<Map<number, OutreachEmailResponse>>(new Map());
  const [sending, setSending] = useState(false);
  const [bulkQueueing, setBulkQueueing] = useState(false);
  
  // Filters and bulk select for "Zonder Email" view
  const [locationCategoryFilter, setLocationCategoryFilter] = useState<string>("");
  const [locationCityFilter, setLocationCityFilter] = useState<string>("");
  const [selectedLocationIds, setSelectedLocationIds] = useState<Set<number>>(new Set());
  const [categoryOptions, setCategoryOptions] = useState<CategoryOption[]>([]);
  const [categoryOptionsLoading, setCategoryOptionsLoading] = useState(false);

  const loadContacts = async () => {
    setLoading(true);
    try {
      const params: { 
        location_id?: number; 
        city?: string;
        email_status?: "all" | "not_sent" | "sent" | "queued";
        limit?: number; 
        offset?: number 
      } = {
        limit: 500,
        offset: 0,
      };
      if (locationIdFilter.trim()) {
        const id = parseInt(locationIdFilter.trim(), 10);
        if (!isNaN(id)) {
          params.location_id = id;
        }
      }
      if (cityFilter) {
        params.city = cityFilter;
      }
      if (emailStatusFilter !== "all") {
        params.email_status = emailStatusFilter;
      }
      const data = await listOutreachContacts(params);
      setContacts(data);
    } catch (error: any) {
      toast.error(`Failed to load contacts: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const loadQueuedContacts = async () => {
    setLoading(true);
    try {
      const params: { 
        location_id?: number; 
        city?: string;
        email_status: "queued";
        limit?: number; 
        offset?: number 
      } = {
        email_status: "queued",
        limit: 500,
        offset: 0,
      };
      if (locationIdFilter.trim()) {
        const id = parseInt(locationIdFilter.trim(), 10);
        if (!isNaN(id)) {
          params.location_id = id;
        }
      }
      if (cityFilter) {
        params.city = cityFilter;
      }
      const data = await listOutreachContacts(params);
      setQueuedContacts(data);
      setQueuedContactsTotal(data.length);
    } catch (error: any) {
      toast.error(`Failed to load queued contacts: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const loadCities = async () => {
    setCitiesLoading(true);
    try {
      const citiesData = await getCities();
      setCities(citiesData);
    } catch (error: any) {
      toast.error(`Failed to load cities: ${error.message}`);
    } finally {
      setCitiesLoading(false);
    }
  };

  const loadLocationsWithoutContact = async (offset: number = 0) => {
    setLoading(true);
    try {
      const params: {
        limit: number;
        offset: number;
        category?: string;
        city?: string;
      } = {
        limit: locationsWithoutContactLimit,
        offset: offset,
      };
      
      if (locationCategoryFilter) {
        params.category = locationCategoryFilter;
      }
      if (locationCityFilter) {
        params.city = locationCityFilter;
      }
      
      const data = await listLocationsWithoutContact(params);
      setLocationsWithoutContact(data.items);
      setLocationsWithoutContactTotal(data.total);
      setLocationsWithoutContactOffset(offset);
    } catch (error: any) {
      toast.error(`Failed to load locations: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const loadCategoryOptions = async () => {
    setCategoryOptionsLoading(true);
    try {
      const categories = await listAdminLocationCategories();
      setCategoryOptions(categories);
    } catch (error: any) {
      console.error("Failed to load category options:", error);
      // Don't show toast - this is not critical
    } finally {
      setCategoryOptionsLoading(false);
    }
  };

  // Load cities and category options on mount
  useEffect(() => {
    loadCities();
    loadCategoryOptions();
  }, []);

  // Load data when filter mode changes
  useEffect(() => {
    if (filterMode === "with_email") {
      loadContacts();
      setSelectedLocationIds(new Set()); // Clear location selection when switching modes
    } else if (filterMode === "queued") {
      loadQueuedContacts();
      setSelectedLocationIds(new Set()); // Clear location selection when switching modes
      setSelectedContactIds(new Set()); // Clear contact selection when switching modes
    } else {
      setLocationsWithoutContactOffset(0); // Reset to first page
      loadLocationsWithoutContact(0);
      setSelectedContactIds(new Set()); // Clear contact selection when switching modes
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterMode]);

  // Reload contacts when filters change (only for with_email mode)
  useEffect(() => {
    if (filterMode === "with_email") {
      loadContacts();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locationIdFilter, cityFilter, emailStatusFilter]);

  // Reload queued contacts when filters change (only for queued mode)
  useEffect(() => {
    if (filterMode === "queued") {
      loadQueuedContacts();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locationIdFilter, cityFilter]);

  // Reload locations when filters change (only for without_email mode)
  useEffect(() => {
    if (filterMode === "without_email") {
      setLocationsWithoutContactOffset(0);
      setSelectedLocationIds(new Set()); // Clear selection when filters change
      loadLocationsWithoutContact(0);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locationCategoryFilter, locationCityFilter]);

  // Note: Email statuses are now included in the contact response, 
  // so we don't need a separate loadEmailStatuses call for display.
  // We still use it for refreshing after queue operations.

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

  const handleToggleSelectLocation = (locationId: number) => {
    setSelectedLocationIds(prev => {
      const next = new Set(prev);
      if (next.has(locationId)) {
        next.delete(locationId);
      } else {
        next.add(locationId);
      }
      return next;
    });
  };

  const handleSelectAllLocations = () => {
    if (selectedLocationIds.size === locationsWithoutContact.length) {
      setSelectedLocationIds(new Set());
    } else {
      setSelectedLocationIds(new Set(locationsWithoutContact.map(l => l.id)));
    }
  };

  const handleBulkAddContacts = async () => {
    if (selectedLocationIds.size === 0) {
      toast.error("Selecteer ten minste één locatie");
      return;
    }
    
    const count = selectedLocationIds.size;
    if (!confirm(`Wil je contacten toevoegen voor ${count} locatie(s)?`)) {
      return;
    }
    
    // For now, open dialog for first selected location
    // Future: could be extended to bulk add dialog
    const firstLocationId = Array.from(selectedLocationIds)[0];
    const location = locationsWithoutContact.find(l => l.id === firstLocationId);
    
    if (location) {
      setSelectedLocationForAdd(location);
      setIsAddDialogOpen(true);
      // Clear selection after opening dialog
      setSelectedLocationIds(new Set());
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

  const handleBulkQueue = async () => {
    if (selectedContactIds.size === 0) {
      toast.error("Please select at least one contact");
      return;
    }

    const selectedContacts = contacts.filter(c => selectedContactIds.has(c.id));
    const locationIds = selectedContacts.map(c => c.location_id);

    if (locationIds.length === 0) {
      toast.error("No valid locations selected");
      return;
    }

    setBulkQueueing(true);
    try {
      const result = await bulkQueueOutreachEmails(locationIds);
      
      let message = `Queued ${result.queued_count} email(s)`;
      const details: string[] = [];
      
      if (result.already_queued_count > 0) {
        details.push(`${result.already_queued_count} already queued`);
      }
      if (result.already_sent_count > 0) {
        details.push(`${result.already_sent_count} already sent`);
      }
      if (result.failed_count > 0) {
        details.push(`${result.failed_count} failed`);
      }
      
      if (details.length > 0) {
        message += ` (${details.join(", ")})`;
      }
      
      if (result.queued_count > 0) {
        toast.success(message);
      } else if (result.failed_count > 0) {
        toast.error(message);
      } else {
        toast.info(message);
      }
      
      if (result.errors.length > 0 && result.errors.length <= 5) {
        result.errors.forEach(error => {
          toast.error(error, { duration: 5000 });
        });
      } else if (result.errors.length > 5) {
        toast.error(`${result.errors.length} errors occurred. Check console for details.`);
        console.error("Bulk queue errors:", result.errors);
      }
      
      // Clear selection
      setSelectedContactIds(new Set());
      
      // Reload email statuses and contacts
      await loadEmailStatuses();
      await loadContacts();
    } catch (error: any) {
      toast.error(`Failed to queue emails: ${error.message}`);
    } finally {
      setBulkQueueing(false);
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
      // Reload all email statuses and current view
      await loadEmailStatuses();
      if (filterMode === "with_email") {
        await loadContacts();
      } else if (filterMode === "queued") {
        await loadQueuedContacts();
      }
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
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={() => {
                    if (filterMode === "with_email") {
                      loadContacts();
                    } else if (filterMode === "queued") {
                      loadQueuedContacts();
                    } else {
                      loadLocationsWithoutContact(locationsWithoutContactOffset);
                    }
                  }}
                >
                  <Icon name="RefreshCw" sizeRem={1} className="mr-2" />
                  Refresh
                </Button>
                {(filterMode === "with_email" || filterMode === "queued") && (
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
                      <>
                        <Button 
                          variant="default" 
                          size="sm" 
                          onClick={handleBulkQueue}
                          disabled={bulkQueueing}
                        >
                          <Icon name="Mail" sizeRem={1} className="mr-2" />
                          {bulkQueueing ? "Queueing..." : `Queue All Selected (${selectedContactIds.size})`}
                        </Button>
                        <Button 
                          variant="destructive" 
                          size="sm" 
                          onClick={handleBulkDelete}
                        >
                          <Icon name="Trash2" sizeRem={1} className="mr-2" />
                          Delete Selected ({selectedContactIds.size})
                        </Button>
                      </>
                    )}
                    <Button size="sm" onClick={() => setIsAddDialogOpen(true)}>
                      <Icon name="Plus" sizeRem={1} className="mr-2" />
                      Add Contact
                    </Button>
                  </>
                )}
                {filterMode === "without_email" && selectedLocationIds.size > 0 && (
                  <Button 
                    variant="default" 
                    size="sm" 
                    onClick={handleBulkAddContacts}
                  >
                    <Icon name="Plus" sizeRem={1} className="mr-2" />
                    Bulk Toevoegen ({selectedLocationIds.size})
                  </Button>
                )}
              </div>
            </div>

            {/* Filter Dropdown */}
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <label className="text-sm font-medium">Weergave:</label>
                <select
                  value={filterMode}
                  onChange={(e) => setFilterMode(e.target.value as FilterMode)}
                  className="w-56 rounded-md border border-input bg-background px-3 py-1.5 text-sm"
                >
                  <option value="with_email">Met Email ({contacts.length})</option>
                  <option value="queued">Gequeued ({queuedContactsTotal})</option>
                  <option value="without_email">Zonder Email ({locationsWithoutContactTotal})</option>
                </select>
              </div>
              {filterMode === "with_email" && (
                <>
                  <div className="flex items-center gap-2">
                    <label className="text-sm font-medium">Email Status:</label>
                    <select
                      value={emailStatusFilter}
                      onChange={(e) => setEmailStatusFilter(e.target.value as EmailStatusFilter)}
                      className="w-40 rounded-md border border-input bg-background px-3 py-1.5 text-sm"
                    >
                      <option value="all">Alle</option>
                      <option value="not_sent">Niet verzonden</option>
                      <option value="sent">Verzonden</option>
                    </select>
                  </div>
                  <div className="flex items-center gap-2">
                    <label className="text-sm font-medium">Stad:</label>
                    <select
                      value={cityFilter}
                      onChange={(e) => setCityFilter(e.target.value)}
                      disabled={citiesLoading}
                      className="w-48 rounded-md border border-input bg-background px-3 py-1.5 text-sm"
                    >
                      <option value="">Alle steden</option>
                      {cities.map((city) => (
                        <option key={city.key} value={city.key}>
                          {city.name}
                        </option>
                      ))}
                    </select>
                  </div>
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
                </>
              )}
              {filterMode === "queued" && (
                <>
                  <div className="flex items-center gap-2">
                    <label className="text-sm font-medium">Stad:</label>
                    <select
                      value={cityFilter}
                      onChange={(e) => setCityFilter(e.target.value)}
                      disabled={citiesLoading}
                      className="w-48 rounded-md border border-input bg-background px-3 py-1.5 text-sm"
                    >
                      <option value="">Alle steden</option>
                      {cities.map((city) => (
                        <option key={city.key} value={city.key}>
                          {city.name}
                        </option>
                      ))}
                    </select>
                  </div>
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
                </>
              )}
              {filterMode === "without_email" && (
                <>
                  <div className="flex items-center gap-2">
                    <label className="text-sm font-medium">Categorie:</label>
                    <select
                      value={locationCategoryFilter}
                      onChange={(e) => {
                        setLocationCategoryFilter(e.target.value);
                        setLocationsWithoutContactOffset(0);
                      }}
                      disabled={categoryOptionsLoading}
                      className="w-48 rounded-md border border-input bg-background px-3 py-1.5 text-sm"
                    >
                      <option value="">Alle categorieën</option>
                      {categoryOptions.map((cat) => (
                        <option key={cat.key} value={cat.key}>
                          {cat.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="flex items-center gap-2">
                    <label className="text-sm font-medium">Stad:</label>
                    <select
                      value={locationCityFilter}
                      onChange={(e) => {
                        setLocationCityFilter(e.target.value);
                        setLocationsWithoutContactOffset(0);
                      }}
                      disabled={citiesLoading}
                      className="w-48 rounded-md border border-input bg-background px-3 py-1.5 text-sm"
                    >
                      <option value="">Alle steden</option>
                      {cities.map((city) => (
                        <option key={city.key} value={city.key}>
                          {city.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </>
              )}
            </div>

            {/* Content based on filter mode */}
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="text-muted-foreground">Loading...</div>
              </div>
            ) : filterMode === "queued" ? (
              /* Queued Contacts */
              queuedContacts.length === 0 ? (
                <div className="flex items-center justify-center py-8">
                  <div className="text-muted-foreground">Geen gequeued emails gevonden</div>
                </div>
              ) : (
                <div className="space-y-2">
                  {/* Select All Checkbox */}
                  <div className="flex items-center gap-2 pb-2 border-b">
                    <input
                      type="checkbox"
                      checked={selectedContactIds.size === queuedContacts.length && queuedContacts.length > 0}
                      onChange={() => {
                        if (selectedContactIds.size === queuedContacts.length) {
                          setSelectedContactIds(new Set());
                        } else {
                          setSelectedContactIds(new Set(queuedContacts.map(c => c.id)));
                        }
                      }}
                      className="w-4 h-4 rounded border-gray-300"
                    />
                    <label className="text-sm font-medium">
                      Select All ({queuedContacts.length})
                    </label>
                  </div>
                  {queuedContacts.map((contact) => (
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
                              <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200">
                                QUEUED
                              </Badge>
                            </div>
                            <div className="text-sm text-muted-foreground space-y-1">
                              <div>
                                <strong>Email:</strong> {contact.email}
                              </div>
                              <div>
                                <strong>Location ID:</strong> {contact.location_id}
                              </div>
                              {contact.city && (
                                <div>
                                  <strong>Stad:</strong> {contact.city}
                                </div>
                              )}
                              <div>
                                <strong>Discovered:</strong> {formatDate(contact.discovered_at)}
                              </div>
                              <div>
                                <strong>Created:</strong> {formatDate(contact.created_at)}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
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
                              {contact.city && (
                                <div>
                                  <strong>Stad:</strong> {contact.city}
                                </div>
                              )}
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
                              const emailStatus = contact.email_status;
                              if (emailStatus) {
                                const statusColors: Record<string, string> = {
                                  queued: "bg-yellow-50 text-yellow-700 border-yellow-200",
                                  sent: "bg-green-50 text-green-700 border-green-200",
                                  delivered: "bg-green-50 text-green-700 border-green-200",
                                  clicked: "bg-blue-50 text-blue-700 border-blue-200",
                                  bounced: "bg-red-50 text-red-700 border-red-200",
                                  opted_out: "bg-gray-50 text-gray-700 border-gray-200",
                                };
                                const colorClass = statusColors[emailStatus] || "bg-gray-50 text-gray-700 border-gray-200";
                                return (
                                  <Badge variant="outline" className={colorClass}>
                                    {emailStatus.toUpperCase()}
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
                    {/* Select All Checkbox */}
                    <div className="flex items-center gap-2 pb-2 border-b">
                      <input
                        type="checkbox"
                        checked={selectedLocationIds.size === locationsWithoutContact.length && locationsWithoutContact.length > 0}
                        onChange={handleSelectAllLocations}
                        className="w-4 h-4 rounded border-gray-300"
                      />
                      <label className="text-sm font-medium">
                        Select All ({locationsWithoutContact.length})
                      </label>
                    </div>
                    {locationsWithoutContact.map((location) => (
                      <Card key={location.id}>
                        <CardContent className="p-4">
                          <div className="flex items-start justify-between gap-3">
                            <input
                              type="checkbox"
                              checked={selectedLocationIds.has(location.id)}
                              onChange={() => handleToggleSelectLocation(location.id)}
                              className="w-4 h-4 mt-1 rounded border-gray-300"
                            />
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

