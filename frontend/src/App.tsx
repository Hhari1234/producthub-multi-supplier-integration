import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, ArrowUpRight, Boxes, Download, Filter, Package2, RefreshCw, ShieldCheck, TrendingUp, UploadCloud } from 'lucide-react';
import { BarChart, Bar, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { apiGet, uploadFeed } from './lib/api';

type Supplier = {
  id: number;
  supplier_code: string;
  name: string;
  status: string;
  supported_format: string;
  total_imported_records: number;
  last_ingestion_at?: string | null;
};

type DashboardData = {
  total_suppliers: number;
  total_products: number;
  rejected_records: number;
  latest_pipeline: string | null;
  latest_duration: number;
  status: string;
};

type Product = {
  id: number;
  product_name: string;
  brand: string;
  category: string;
  price: number;
  stock: number;
  updated_at: string;
  model_number?: string | null;
  selected_supplier_name?: string | null;
  selection_reason?: string | null;
};

type Run = {
  run_id: string;
  status: string;
  total_input_records: number;
  valid_records: number;
  rejected_records: number;
  inserted_records: number;
  updated_records: number;
  processing_duration: number;
  failure_reason?: string | null;
  start_time?: string | null;
  end_time?: string | null;
};

type Reject = {
  id: number;
  supplier_id: number;
  source_file: string;
  run_id: string;
  rejection_reason: string;
  original_payload: Record<string, unknown>;
  created_at: string;
};

type TraceabilityResponse = {
  product_id: number;
  product_name: string;
  traceability: Array<{
    supplier: string | null;
    supplier_product_id: string;
    source_file: string;
    source_record_key: string;
    raw_payload: Record<string, unknown> | null;
    matched_value: string | null;
  }>;
};

type ReportsResponse = {
  reconciliation: {
    total_input_records: number;
    valid_records: number;
    rejected_records: number;
    difference: number;
    supplier_totals: Record<string, number>;
    product_count: number;
  };
  quality: Record<string, number>;
  supplier_contribution: Record<string, number>;
};

const tabs = [
  'Dashboard',
  'Suppliers',
  'Upload',
  'Catalogue',
  'Traceability',
  'Quality',
  'Pipeline',
  'Reports',
];

const formatNumber = (value: number) => new Intl.NumberFormat().format(value);

export default function App() {
  const [activeTab, setActiveTab] = useState('Dashboard');
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [rejects, setRejects] = useState<Reject[]>([]);
  const [reports, setReports] = useState<ReportsResponse | null>(null);
  const [productId, setProductId] = useState<number | null>(null);
  const [traceability, setTraceability] = useState<TraceabilityResponse | null>(null);
  const [selectedSupplier, setSelectedSupplier] = useState<number>(0);
  const [file, setFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [brandFilter, setBrandFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [supplierFilter, setSupplierFilter] = useState('');
  const [sortOrder, setSortOrder] = useState('price_asc');

  const loadData = async () => {
    setLoading(true);
    try {
      const [supplierData, dashboardData, reportsData, productData, runData, rejectData] = await Promise.all([
        apiGet<Supplier[]>('/suppliers'),
        apiGet<DashboardData>('/dashboard'),
        apiGet<ReportsResponse>('/reports'),
        apiGet<Product[]>('/products'),
        apiGet<Run[]>('/pipeline/runs'),
        apiGet<Reject[]>('/quality/rejects'),
      ]);
      setSuppliers(supplierData);
      setDashboard(dashboardData);
      setReports(reportsData);
      setProducts(productData);
      setRuns(runData);
      setRejects(rejectData);
      if (supplierData.length > 0 && !selectedSupplier) {
        setSelectedSupplier(supplierData[0].id);
      }
    } catch (error) {
      setUploadStatus(((error as Error).message) || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const filteredProducts = useMemo(() => {
    return products.filter((product) => {
      const brandMatch = !brandFilter || product.brand.toLowerCase().includes(brandFilter.toLowerCase());
      const categoryMatch = !categoryFilter || product.category.toLowerCase().includes(categoryFilter.toLowerCase());
      const supplierMatch = !supplierFilter || (product.selected_supplier_name || '').toLowerCase().includes(supplierFilter.toLowerCase());
      return brandMatch && categoryMatch && supplierMatch;
    }).sort((a, b) => sortOrder === 'price_desc' ? b.price - a.price : a.price - b.price);
  }, [products, brandFilter, categoryFilter, supplierFilter, sortOrder]);

  useEffect(() => {
    void loadData();
  }, []);

  const chartData = reports ? Object.entries(reports.reconciliation.supplier_totals).map(([name, value]) => ({ name, value })) : [];

  const handleUpload = async () => {
    if (!file || !selectedSupplier) {
      setUploadStatus('Please choose a supplier and a file.');
      return;
    }

    try {
      setLoading(true);
      const result = await uploadFeed(selectedSupplier, file);
      setUploadStatus(`Upload successful: ${result.run_id} (${result.valid_records} valid, ${result.rejected_records} rejected)`);
      await loadData();
    } catch (error) {
      setUploadStatus((error as Error).message || 'Upload failed');
    } finally {
      setLoading(false);
    }
  };

  const viewTraceability = async (productIdValue: number) => {
    try {
      setProductId(productIdValue);
      const data = await apiGet<TraceabilityResponse>(`/products/${productIdValue}/traceability`);
      setTraceability(data);
      setActiveTab('Traceability');
    } catch (error) {
      setUploadStatus((error as Error).message || 'Unable to load traceability');
    }
  };

  return (
    <div className="min-h-screen bg-slate-100 text-slate-800">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.2em] text-blue-600">ProductHub</div>
            <h1 className="text-xl font-semibold">Data operations dashboard</h1>
          </div>
          <button
            className="inline-flex items-center gap-2 rounded border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            onClick={() => void loadData()}
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-6 py-6">
        <nav className="mb-6 flex flex-wrap gap-2">
          {tabs.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`rounded-full px-3 py-2 text-sm font-medium ${activeTab === tab ? 'bg-blue-600 text-white' : 'bg-white text-slate-700 border border-slate-200'}`}
            >
              {tab}
            </button>
          ))}
        </nav>

        {loading && <div className="mb-4 rounded border border-blue-200 bg-blue-50 p-3 text-sm text-blue-700">Loading data…</div>}
        {uploadStatus && <div className="mb-4 rounded border border-slate-200 bg-white p-3 text-sm text-slate-700">{uploadStatus}</div>}

        {activeTab === 'Dashboard' && dashboard && (
          <div className="space-y-6">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
              {[
                { label: 'Total suppliers', value: dashboard.total_suppliers, icon: Boxes },
                { label: 'Unified products', value: dashboard.total_products, icon: Package2 },
                { label: 'Rejected records', value: dashboard.rejected_records, icon: AlertTriangle },
                { label: 'Latest pipeline', value: dashboard.latest_pipeline || 'N/A', icon: TrendingUp },
                { label: 'Processing duration', value: `${dashboard.latest_duration.toFixed(2)}s`, icon: ArrowUpRight },
              ].map(({ label, value, icon: Icon }) => (
                <div key={label} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-500">{label}</span>
                    <Icon className="h-4 w-4 text-blue-600" />
                  </div>
                  <div className="mt-3 text-2xl font-semibold">{value}</div>
                </div>
              ))}
            </div>
            <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <h3 className="mb-4 text-lg font-semibold">Supplier contribution</h3>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="value" fill="#2563eb" radius={[6, 6, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <h3 className="mb-4 text-lg font-semibold">Data quality summary</h3>
                <ul className="space-y-3 text-sm text-slate-700">
                  <li className="flex items-center justify-between border-b border-slate-100 pb-2"><span>Latest run</span><strong>{dashboard.latest_pipeline || 'none'}</strong></li>
                  <li className="flex items-center justify-between border-b border-slate-100 pb-2"><span>Status</span><strong>{dashboard.status}</strong></li>
                  <li className="flex items-center justify-between border-b border-slate-100 pb-2"><span>Total rejected</span><strong>{formatNumber(dashboard.rejected_records)}</strong></li>
                  <li className="flex items-center justify-between"><span>Duration</span><strong>{dashboard.latest_duration.toFixed(2)}s</strong></li>
                </ul>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'Suppliers' && (
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="mb-4 text-lg font-semibold">Supplier management</h3>
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-slate-600">
                  <tr>
                    <th className="p-3">Supplier</th>
                    <th className="p-3">Status</th>
                    <th className="p-3">Format</th>
                    <th className="p-3">Imported</th>
                    <th className="p-3">Last ingestion</th>
                  </tr>
                </thead>
                <tbody>
                  {suppliers.map((supplier) => (
                    <tr key={supplier.id} className="border-t border-slate-100">
                      <td className="p-3">{supplier.name} ({supplier.supplier_code})</td>
                      <td className="p-3"><span className="rounded-full bg-emerald-100 px-2 py-1 text-xs font-medium text-emerald-700">{supplier.status}</span></td>
                      <td className="p-3">{supplier.supported_format}</td>
                      <td className="p-3">{formatNumber(supplier.total_imported_records)}</td>
                      <td className="p-3">{supplier.last_ingestion_at ? new Date(supplier.last_ingestion_at).toLocaleString() : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'Upload' && (
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="mb-4 text-lg font-semibold">Upload feed</h3>
            <div className="grid gap-4 md:grid-cols-3">
              <select
                value={selectedSupplier}
                onChange={(event) => setSelectedSupplier(Number(event.target.value))}
                className="rounded border border-slate-300 bg-white p-3"
              >
                {suppliers.map((supplier) => (
                  <option key={supplier.id} value={supplier.id}>{supplier.name}</option>
                ))}
              </select>
              <input type="file" onChange={(event) => setFile(event.target.files?.[0] || null)} className="rounded border border-slate-300 bg-white p-3" />
              <button onClick={() => void handleUpload()} className="flex items-center justify-center gap-2 rounded bg-blue-600 px-4 py-3 font-medium text-white hover:bg-blue-700">
                <UploadCloud className="h-4 w-4" />
                Start pipeline
              </button>
            </div>
          </div>
        )}

        {activeTab === 'Catalogue' && (
          <div className="space-y-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="grid gap-3 md:grid-cols-4">
                <input value={brandFilter} onChange={(e) => setBrandFilter(e.target.value)} placeholder="Filter by brand" className="rounded border border-slate-300 p-3" />
                <input value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)} placeholder="Filter by category" className="rounded border border-slate-300 p-3" />
                <input value={supplierFilter} onChange={(e) => setSupplierFilter(e.target.value)} placeholder="Filter by supplier" className="rounded border border-slate-300 p-3" />
                <select value={sortOrder} onChange={(e) => setSortOrder(e.target.value)} className="rounded border border-slate-300 p-3">
                  <option value="price_asc">Sort by price: low to high</option>
                  <option value="price_desc">Sort by price: high to low</option>
                </select>
              </div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="p-3">Product</th>
                      <th className="p-3">Brand</th>
                      <th className="p-3">Category</th>
                      <th className="p-3">Price</th>
                      <th className="p-3">Stock</th>
                      <th className="p-3">Supplier</th>
                      <th className="p-3">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredProducts.map((product) => (
                      <tr key={product.id} className="border-t border-slate-100">
                        <td className="p-3">{product.product_name}</td>
                        <td className="p-3">{product.brand}</td>
                        <td className="p-3">{product.category}</td>
                        <td className="p-3">${Number(product.price).toFixed(2)}</td>
                        <td className="p-3">{product.stock}</td>
                        <td className="p-3">{product.selected_supplier_name}</td>
                        <td className="p-3"><button onClick={() => void viewTraceability(product.id)} className="text-blue-600 hover:underline">Trace</button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'Traceability' && (
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="mb-4 text-lg font-semibold">Product traceability</h3>
            {traceability ? (
              <div>
                <div className="mb-4 rounded bg-slate-50 p-3">
                  <div className="text-sm text-slate-500">Product</div>
                  <div className="text-lg font-semibold">{traceability.product_name}</div>
                </div>
                <div className="space-y-3">
                  {traceability.traceability.map((item, index) => (
                    <div key={`${item.supplier}-${item.source_file}-${index}`} className="rounded border border-slate-200 p-3">
                      <div className="mb-2 flex items-center justify-between"><strong>{item.supplier}</strong><span className="text-xs text-slate-500">{item.source_file}</span></div>
                      <div className="grid gap-2 text-sm text-slate-600 md:grid-cols-2">
                        <div><span className="font-medium text-slate-700">Supplier product id:</span> {item.supplier_product_id}</div>
                        <div><span className="font-medium text-slate-700">Matched value:</span> {item.matched_value || '—'}</div>
                        <div className="md:col-span-2"><span className="font-medium text-slate-700">Original payload:</span> <pre className="mt-1 overflow-auto rounded bg-slate-50 p-2 text-xs">{JSON.stringify(item.raw_payload, null, 2)}</pre></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-slate-500">Select a product to view supplier history.</div>
            )}
          </div>
        )}

        {activeTab === 'Quality' && (
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="mb-4 text-lg font-semibold">Data quality rejects</h3>
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="p-3">Run</th>
                    <th className="p-3">Supplier</th>
                    <th className="p-3">File</th>
                    <th className="p-3">Reason</th>
                    <th className="p-3">Payload</th>
                  </tr>
                </thead>
                <tbody>
                  {rejects.map((reject) => (
                    <tr key={reject.id} className="border-t border-slate-100 align-top">
                      <td className="p-3">{reject.run_id}</td>
                      <td className="p-3">{reject.supplier_id}</td>
                      <td className="p-3">{reject.source_file}</td>
                      <td className="p-3">{reject.rejection_reason}</td>
                      <td className="p-3"><pre className="max-w-md overflow-auto text-xs">{JSON.stringify(reject.original_payload, null, 2)}</pre></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'Pipeline' && (
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="mb-4 text-lg font-semibold">Pipeline runs</h3>
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="p-3">Run</th>
                    <th className="p-3">Status</th>
                    <th className="p-3">Input</th>
                    <th className="p-3">Valid</th>
                    <th className="p-3">Rejected</th>
                    <th className="p-3">Inserted</th>
                    <th className="p-3">Updated</th>
                    <th className="p-3">Duration</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((run) => (
                    <tr key={run.run_id} className="border-t border-slate-100">
                      <td className="p-3">{run.run_id}</td>
                      <td className="p-3">{run.status}</td>
                      <td className="p-3">{run.total_input_records}</td>
                      <td className="p-3">{run.valid_records}</td>
                      <td className="p-3">{run.rejected_records}</td>
                      <td className="p-3">{run.inserted_records}</td>
                      <td className="p-3">{run.updated_records}</td>
                      <td className="p-3">{run.processing_duration}s</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'Reports' && reports && (
          <div className="space-y-6">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"><div className="text-sm text-slate-500">Input records</div><div className="mt-2 text-2xl font-semibold">{formatNumber(reports.reconciliation.total_input_records)}</div></div>
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"><div className="text-sm text-slate-500">Valid records</div><div className="mt-2 text-2xl font-semibold">{formatNumber(reports.reconciliation.valid_records)}</div></div>
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"><div className="text-sm text-slate-500">Rejected records</div><div className="mt-2 text-2xl font-semibold">{formatNumber(reports.reconciliation.rejected_records)}</div></div>
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"><div className="text-sm text-slate-500">Unified products</div><div className="mt-2 text-2xl font-semibold">{formatNumber(reports.reconciliation.product_count)}</div></div>
            </div>
            <div className="grid gap-6 lg:grid-cols-2">
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <h3 className="mb-4 text-lg font-semibold">Reconciliation</h3>
                <ul className="space-y-2 text-sm text-slate-700">
                  {Object.entries(reports.reconciliation.supplier_totals).map(([key, value]) => (
                    <li key={key} className="flex justify-between border-b border-slate-100 pb-2"><span>{key}</span><span>{value}</span></li>
                  ))}
                </ul>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <h3 className="mb-4 text-lg font-semibold">Quality report</h3>
                <ul className="space-y-2 text-sm text-slate-700">
                  {Object.entries(reports.quality).map(([key, value]) => (
                    <li key={key} className="flex justify-between border-b border-slate-100 pb-2"><span>{key}</span><span>{value}</span></li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
