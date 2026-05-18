import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";

const candidates = [
  {
    city: "Lisbon",
    country: "Portugal",
    score: 91,
    climate: "17-28C",
    rain: "4 mm rain",
    air: "Good air",
    status: "ready",
    summary:
      "Compact neighborhoods, late trains, and a strong attraction base make Lisbon a high-confidence long-weekend match.",
  },
  {
    city: "Porto",
    country: "Portugal",
    score: 86,
    climate: "15-24C",
    rain: "8 mm rain",
    air: "Good air",
    status: "details-loading",
    summary:
      "Riverfront walks and dense central sights score well, with details still hydrating from stored and live sources.",
  },
  {
    city: "Milan",
    country: "Italy",
    score: 79,
    climate: "18-27C",
    rain: "12 mm rain",
    air: "Moderate air",
    status: "details-failed",
    summary:
      "Strong access and population context, but one scoring dependency failed after retries.",
  },
  {
    city: "Rome",
    country: "Italy",
    score: null,
    climate: null,
    rain: null,
    air: null,
    status: "scoring",
    summary: "",
  },
];

function ResultCard({ item }: { item: (typeof candidates)[number] }) {
  const isBodyLoading = item.status === "scoring" || item.status === "details-loading";
  const detailsFailed = item.status === "details-failed";

  return (
    <Card className="flex h-[260px] flex-col rounded-lg">
      <CardHeader className="flex-row items-start justify-between gap-3">
        <div className="min-w-0">
          <CardTitle className="truncate text-base">
            {item.city}, {item.country}
          </CardTitle>
        </div>
        {typeof item.score === "number" ? <Badge variant="secondary">{item.score}</Badge> : null}
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-3">
        {isBodyLoading ? (
          <>
            <div className="flex flex-wrap gap-2">
              <Skeleton className="h-5 w-16" />
              <Skeleton className="h-5 w-20" />
              <Skeleton className="h-5 w-16" />
            </div>
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-11/12" />
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="mt-auto h-8 w-full" />
          </>
        ) : (
          <>
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline">{item.climate ?? "N/A"}</Badge>
              <Badge variant="outline">{item.rain ?? "N/A"}</Badge>
              <Badge variant={item.air === "Good air" ? "secondary" : "outline"}>
                {item.air ?? "N/A"}
              </Badge>
            </div>
            <p className="line-clamp-3 text-sm text-muted-foreground">
              {detailsFailed ? "N/A" : item.summary}
            </p>
            <div className="mt-auto">
              {detailsFailed ? (
                <Button className="w-full" size="sm" variant="outline">
                  Retry details
                </Button>
              ) : null}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function Controls() {
  return (
    <Card className="rounded-lg">
      <CardHeader>
        <CardTitle className="text-base">Search controls</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="grid grid-cols-2 gap-2">
          <Input readOnly value="1800 km" aria-label="Radius" />
          <Input readOnly value="250k+" aria-label="Population" />
        </div>
        <Button>
          <Spinner aria-hidden="true" />
          Scoring cities 7/10
        </Button>
      </CardContent>
    </Card>
  );
}

function OptionA() {
  return (
    <section className="grid gap-4 lg:grid-cols-[300px_1fr]">
      <Controls />
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {candidates.map((item) => (
          <ResultCard item={item} key={item.city} />
        ))}
      </div>
    </section>
  );
}

function OptionB() {
  return (
    <section className="grid min-h-[620px] gap-4 lg:grid-cols-[280px_1fr_280px]">
      <Controls />
      <Card className="rounded-lg">
        <CardHeader>
          <CardTitle className="text-base">Destination map and live ranking</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2">
          {candidates.map((item) => (
            <ResultCard item={item} key={item.city} />
          ))}
        </CardContent>
      </Card>
      <Card className="rounded-lg">
        <CardHeader>
          <CardTitle className="text-base">Request progress</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {["Cities found 10/10", "Scored 7/10", "Details loaded 5/10"].map((label, index) => (
            <div className="flex flex-col gap-2" key={label}>
              <div className="flex items-center justify-between text-sm">
                <span>{label}</span>
                <Badge variant="outline">{index === 0 ? "done" : "active"}</Badge>
              </div>
              <Progress value={[100, 70, 50][index]} />
            </div>
          ))}
        </CardContent>
      </Card>
    </section>
  );
}

function OptionC() {
  return (
    <section className="grid gap-4 lg:grid-cols-[360px_1fr]">
      <Card className="rounded-lg">
        <CardHeader>
          <CardTitle className="text-base">Candidate queue</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {["Lisbon", "Porto", "Milan", "Rome", "Prague", "Copenhagen"].map((city, index) => (
            <div className="flex items-center justify-between rounded-md border p-3" key={city}>
              <span className="text-sm">{city}</span>
              <Badge variant={index < 3 ? "secondary" : "outline"}>{index < 3 ? "ready" : "waiting"}</Badge>
            </div>
          ))}
        </CardContent>
      </Card>
      <div className="grid gap-3 md:grid-cols-2">
        {candidates.map((item) => (
          <ResultCard item={item} key={item.city} />
        ))}
      </div>
    </section>
  );
}

export default function SearchFlowMockPage() {
  return (
    <main className="min-h-screen bg-background p-6 text-foreground">
      <div className="mx-auto flex max-w-7xl flex-col gap-8">
        <header className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div className="flex flex-col gap-2">
            <Badge className="w-fit" variant="outline">
              Temporary mock
            </Badge>
            <h1 className="text-3xl font-semibold tracking-normal">Parallel recommendation search</h1>
            <p className="max-w-3xl text-muted-foreground">
              Choose the direction for the real search UI: skeleton cards from candidate cities, real
              scoring progress, equal-height cards, card-level retry, and detail hydration.
            </p>
          </div>
          <Card className="w-full rounded-lg md:w-[320px]">
            <CardContent className="flex items-center gap-2 pt-4">
              <Input readOnly value="London, GB" aria-label="Home city" />
              <Button variant="outline">Change</Button>
            </CardContent>
          </Card>
        </header>

        <div className="flex flex-col gap-8">
          <div className="flex flex-col gap-3">
            <h2 className="text-xl font-semibold tracking-normal">Option A: compact operations view</h2>
            <OptionA />
          </div>

          <div className="flex flex-col gap-3">
            <h2 className="text-xl font-semibold tracking-normal">Option B: progress rail</h2>
            <OptionB />
          </div>

          <div className="flex flex-col gap-3">
            <h2 className="text-xl font-semibold tracking-normal">Option C: candidate queue</h2>
            <OptionC />
          </div>
        </div>
      </div>
    </main>
  );
}
