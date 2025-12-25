import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Icon } from "@/components/Icon";
import {
  listOutreachContacts,
  deleteOutreachContact,
  listLocationsWithoutContact,
  type AdminContactResponse,
  type LocationWithoutContact,
} from "@/lib/apiAdmin";
import { toast } from "sonner";
import AddContactDialog from "./AddContactDialog";

type FilterMode = "with_email" | "without_email";

export default function OutreachContactsList() {
  const [filterMode, setFilterMode] = useState<FilterMode>("with_email");
  const [contacts, setContacts] = useState<AdminContactResponse[]>([]);
  const [locationsWithoutContact, setLocationsWithoutContact] = useState<LocationWithoutContact[]>([]);
  const [loading, setLoading] = useState(false);
  const [locationIdFilter, setLocationIdFilter] = useState<string>("");
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [selectedLocationForAdd, setSelectedLocationForAdd] = useState<LocationWithoutContact | null>(null);

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

  const loadLocationsWithoutContact = async () => {
    setLoading(true);
    try {
      const data = await listLocationsWithoutContact({
        limit: 500,
        offset: 0,
      });
      setLocationsWithoutContact(data);
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
      loadLocationsWithoutContact();
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

  const handleAddContactForLocation = (location: LocationWithoutContact) => {
    setSelectedLocationForAdd(location);
    setIsAddDialogOpen(true);
  };

  const handleContactCreated = () => {
    loadContacts();
    loadLocationsWithoutContact();
    setSelectedLocationForAdd(null);
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
                <Button variant="outline" size="sm" onClick={filterMode === "with_email" ? loadContacts : loadLocationsWithoutContact}>
                  <Icon name="RefreshCw" sizeRem={1} className="mr-2" />
                  Refresh
                </Button>
                {filterMode === "with_email" && (
                  <Button size="sm" onClick={() => setIsAddDialogOpen(true)}>
                    <Icon name="Plus" sizeRem={1} className="mr-2" />
                    Add Contact
                  </Button>
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
                    Zonder Email ({locationsWithoutContact.length})
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
                  {contacts.map((contact) => (
                    <Card key={contact.id}>
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between">
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
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDelete(contact.id)}
                            className="text-red-600 hover:text-red-700"
                          >
                            <Icon name="Trash2" sizeRem={1} />
                          </Button>
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

