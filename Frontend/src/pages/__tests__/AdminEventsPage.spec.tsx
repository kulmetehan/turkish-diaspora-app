import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, beforeEach, beforeAll, vi, it } from "vitest";
import { MemoryRouter } from "react-router-dom";

import AdminEventsPage from "@/pages/AdminEventsPage";

const mockListEventCandidatesAdmin = vi.hoisted(() => vi.fn());
const mockVerifyAdminEvent = vi.hoisted(() => vi.fn());
const mockPublishAdminEvent = vi.hoisted(() => vi.fn());
const mockRejectAdminEvent = vi.hoisted(() => vi.fn());
const mockGetDuplicates = vi.hoisted(() => vi.fn());
const mockToast = vi.hoisted(() => ({
    success: vi.fn(),
    error: vi.fn(),
}));

vi.mock("sonner", () => ({
    toast: mockToast,
}));

vi.mock("@/lib/apiAdmin", () => ({
    listEventCandidatesAdmin: (...args: unknown[]) => mockListEventCandidatesAdmin(...args),
    verifyEventCandidateAdmin: (...args: unknown[]) => mockVerifyAdminEvent(...args),
    publishEventCandidateAdmin: (...args: unknown[]) => mockPublishAdminEvent(...args),
    rejectEventCandidateAdmin: (...args: unknown[]) => mockRejectAdminEvent(...args),
    getEventCandidateDuplicatesAdmin: (...args: unknown[]) => mockGetDuplicates(...args),
}));

vi.mock("@/hooks/useAdminEventSources", () => ({
    useAdminEventSources: () => ({
        sources: [{ id: 1, key: "rotterdam_culture", name: "Rotterdam Culture" }],
        loading: false,
        error: null,
        refresh: vi.fn(),
        setSources: vi.fn(),
    }),
}));

const SAMPLE_RESPONSE = {
    items: [
        {
            id: 1,
            event_source_id: 5,
            source_key: "rotterdam_culture",
            source_name: "Rotterdam Culture",
            title: "Community Meetup",
            description: "Desc",
            location_text: "Rotterdam",
            url: "https://example.com",
            start_time_utc: new Date().toISOString(),
            end_time_utc: null,
            duplicate_of_id: null,
            duplicate_score: null,
            has_duplicates: true,
            state: "candidate",
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
        },
    ],
    total: 1,
    limit: 25,
    offset: 0,
};

describe("AdminEventsPage", () => {
    beforeAll(() => {
        window.HTMLElement.prototype.scrollIntoView = vi.fn();
    });

    beforeEach(() => {
        mockListEventCandidatesAdmin.mockReset();
        mockVerifyAdminEvent.mockReset();
        mockPublishAdminEvent.mockReset();
        mockRejectAdminEvent.mockReset();
        mockGetDuplicates.mockReset();
        mockToast.success.mockReset();
        mockToast.error.mockReset();
        mockListEventCandidatesAdmin.mockResolvedValue(SAMPLE_RESPONSE);
    });

    const renderPage = () =>
        render(
            <MemoryRouter>
                <AdminEventsPage />
            </MemoryRouter>,
        );

    it("renders events table with data", async () => {
        renderPage();

        await waitFor(() => {
            expect(screen.getAllByText("Community Meetup").length).toBeGreaterThan(0);
        });

        expect(mockListEventCandidatesAdmin).toHaveBeenCalled();
    });

    it("triggers verify action", async () => {
        mockVerifyAdminEvent.mockResolvedValue(SAMPLE_RESPONSE.items[0]);
        renderPage();

        await waitFor(() => {
            expect(screen.getAllByText("Community Meetup").length).toBeGreaterThan(0);
        });

        const verifyButton = screen.getAllByRole("button", { name: /verify/i })[0];
        fireEvent.click(verifyButton);

        await waitFor(() => {
            expect(mockVerifyAdminEvent).toHaveBeenCalledWith(1);
        });

        expect(mockToast.success).toHaveBeenCalled();
    });

    it("applies duplicates filter", async () => {
        renderPage();
        await waitFor(() => {
            expect(mockListEventCandidatesAdmin).toHaveBeenCalled();
        });

        const duplicatesTrigger = screen.getByLabelText("Duplicates");
        fireEvent.click(duplicatesTrigger);
        const option = await screen.findByText("Duplicates only");
        fireEvent.click(option);

        await waitFor(() => {
            expect(mockListEventCandidatesAdmin).toHaveBeenLastCalledWith(
                expect.objectContaining({
                    duplicatesOnly: true,
                    canonicalOnly: false,
                }),
            );
        });
    });

    it("opens duplicates dialog", async () => {
        mockGetDuplicates.mockResolvedValue({
            canonical: SAMPLE_RESPONSE.items[0],
            duplicates: [
                {
                    ...SAMPLE_RESPONSE.items[0],
                    id: 2,
                    title: "Duplicate Event",
                    duplicate_of_id: 1,
                    duplicate_score: 0.9,
                    has_duplicates: false,
                },
            ],
        });

        renderPage();
        await waitFor(() => {
            expect(screen.getAllByText("Community Meetup").length).toBeGreaterThan(0);
        });

        const viewButton = screen.getAllByRole("button", { name: /view duplicates/i })[0];
        fireEvent.click(viewButton);

        await waitFor(() => {
            expect(mockGetDuplicates).toHaveBeenCalledWith(1);
        });

        await waitFor(() => {
            expect(screen.getByText("Duplicate Event")).toBeTruthy();
        });
    });
});


