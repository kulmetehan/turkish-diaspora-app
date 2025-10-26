import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function AdminHomePage() {
    return (
        <div className="p-6">
            <Card>
                <CardHeader><CardTitle>Admin Area - Auth OK</CardTitle></CardHeader>
                <CardContent>Protected content placeholder.</CardContent>
            </Card>
        </div>
    );
}


