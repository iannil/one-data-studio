/**
 * ONE-DATA-STUDIO Cost Report Page
 * Sprint 32: Developer Experience Optimization
 *
 * Admin page for viewing token usage and cost analytics.
 */

import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  CircularProgress,
  Alert,
  Tabs,
  Tab,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  TextField,
  Stack,
  Chip,
  LinearProgress,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Token as TokenIcon,
  AttachMoney as MoneyIcon,
  Speed as SpeedIcon,
  Refresh as RefreshIcon,
  Download as DownloadIcon,
  FilterList as FilterIcon,
} from '@mui/icons-material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { useTranslation } from 'react-i18next';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as ChartTooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

// Types
interface CostSummary {
  total_cost: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  call_count: number;
  avg_cost_per_call: number;
  avg_tokens_per_call: number;
  by_model: Record<string, { cost: number; tokens: number; calls: number }>;
  by_user: Record<string, { cost: number; tokens: number; calls: number }>;
  by_workflow: Record<string, { cost: number; tokens: number; calls: number }>;
  currency: string;
  period_start: string;
  period_end: string;
}

interface DailyBreakdown {
  date: string;
  cost: number;
  tokens: number;
  calls: number;
}

interface CostRecord {
  id: string;
  timestamp: string;
  user_id: string;
  tenant_id: string;
  workflow_id: string | null;
  model: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost: number;
  execution_time_ms: number;
}

// API functions
const api = {
  getSummary: async (
    tenantId: string,
    startDate: Date,
    endDate: Date
  ): Promise<CostSummary> => {
    const params = new URLSearchParams({
      tenant_id: tenantId,
      start_date: startDate.toISOString(),
      end_date: endDate.toISOString(),
    });
    const response = await fetch(`/api/v1/admin/costs/summary?${params}`);
    if (!response.ok) throw new Error('Failed to fetch cost summary');
    return response.json();
  },

  getDailyBreakdown: async (
    tenantId: string,
    days: number
  ): Promise<DailyBreakdown[]> => {
    const params = new URLSearchParams({
      tenant_id: tenantId,
      days: days.toString(),
    });
    const response = await fetch(`/api/v1/admin/costs/daily?${params}`);
    if (!response.ok) throw new Error('Failed to fetch daily breakdown');
    return response.json();
  },

  getRecords: async (
    tenantId: string,
    page: number,
    pageSize: number
  ): Promise<{ records: CostRecord[]; total: number }> => {
    const params = new URLSearchParams({
      tenant_id: tenantId,
      page: page.toString(),
      page_size: pageSize.toString(),
    });
    const response = await fetch(`/api/v1/admin/costs/records?${params}`);
    if (!response.ok) throw new Error('Failed to fetch records');
    return response.json();
  },

  exportCSV: async (tenantId: string, startDate: Date, endDate: Date): Promise<void> => {
    const params = new URLSearchParams({
      tenant_id: tenantId,
      start_date: startDate.toISOString(),
      end_date: endDate.toISOString(),
      format: 'csv',
    });
    const response = await fetch(`/api/v1/admin/costs/export?${params}`);
    if (!response.ok) throw new Error('Failed to export');
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cost-report-${startDate.toISOString().split('T')[0]}.csv`;
    a.click();
  },
};

// Chart colors
const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82ca9d'];

// Helper components
const StatCard: React.FC<{
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  trend?: number;
  color?: string;
}> = ({ title, value, subtitle, icon, trend, color = 'primary.main' }) => (
  <Card elevation={0} sx={{ height: '100%' }}>
    <CardContent>
      <Box display="flex" justifyContent="space-between" alignItems="flex-start">
        <Box>
          <Typography color="text.secondary" variant="caption" gutterBottom>
            {title}
          </Typography>
          <Typography variant="h4" fontWeight="bold" color={color}>
            {value}
          </Typography>
          {subtitle && (
            <Typography variant="body2" color="text.secondary">
              {subtitle}
            </Typography>
          )}
        </Box>
        <Box
          sx={{
            p: 1,
            borderRadius: 2,
            bgcolor: `${color}15`,
            color: color,
          }}
        >
          {icon}
        </Box>
      </Box>
      {trend !== undefined && (
        <Box display="flex" alignItems="center" mt={1}>
          {trend >= 0 ? (
            <TrendingUpIcon fontSize="small" color="error" />
          ) : (
            <TrendingDownIcon fontSize="small" color="success" />
          )}
          <Typography
            variant="caption"
            color={trend >= 0 ? 'error.main' : 'success.main'}
            ml={0.5}
          >
            {Math.abs(trend).toFixed(1)}% vs last period
          </Typography>
        </Box>
      )}
    </CardContent>
  </Card>
);

const formatCurrency = (value: number, currency: string = 'USD'): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(value);
};

const formatNumber = (value: number): string => {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(2)}K`;
  return value.toFixed(0);
};

// Main component
export const CostReportPage: React.FC = () => {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState(0);

  // Filters
  const [tenantId, setTenantId] = useState('default');
  const [dateRange, setDateRange] = useState<[Date, Date]>([
    new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
    new Date(),
  ]);
  const [periodDays, setPeriodDays] = useState(30);

  // Data
  const [summary, setSummary] = useState<CostSummary | null>(null);
  const [dailyData, setDailyData] = useState<DailyBreakdown[]>([]);
  const [records, setRecords] = useState<CostRecord[]>([]);
  const [recordsTotal, setRecordsTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(25);

  // Load data
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);

        const [summaryData, dailyBreakdown] = await Promise.all([
          api.getSummary(tenantId, dateRange[0], dateRange[1]),
          api.getDailyBreakdown(tenantId, periodDays),
        ]);

        setSummary(summaryData);
        setDailyData(dailyBreakdown);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [tenantId, dateRange, periodDays]);

  // Load records when tab changes to records view
  useEffect(() => {
    if (tabValue === 2) {
      const loadRecords = async () => {
        try {
          const data = await api.getRecords(tenantId, page, pageSize);
          setRecords(data.records);
          setRecordsTotal(data.total);
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Failed to load records');
        }
      };
      loadRecords();
    }
  }, [tabValue, tenantId, page, pageSize]);

  // Prepare chart data
  const modelChartData = useMemo(() => {
    if (!summary) return [];
    return Object.entries(summary.by_model).map(([model, data]) => ({
      name: model,
      cost: data.cost,
      tokens: data.tokens,
      calls: data.calls,
    }));
  }, [summary]);

  const userChartData = useMemo(() => {
    if (!summary) return [];
    return Object.entries(summary.by_user)
      .map(([user, data]) => ({
        name: user,
        cost: data.cost,
        tokens: data.tokens,
      }))
      .sort((a, b) => b.cost - a.cost)
      .slice(0, 10);
  }, [summary]);

  // Handle export
  const handleExport = async () => {
    try {
      await api.exportCSV(tenantId, dateRange[0], dateRange[1]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export');
    }
  };

  if (loading && !summary) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box p={3}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h5" fontWeight="bold">
          {t('admin.costReport', 'Cost Report')}
        </Typography>
        <Stack direction="row" spacing={2}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>{t('admin.period', 'Period')}</InputLabel>
            <Select
              value={periodDays}
              label={t('admin.period', 'Period')}
              onChange={(e) => setPeriodDays(e.target.value as number)}
            >
              <MenuItem value={7}>7 days</MenuItem>
              <MenuItem value={14}>14 days</MenuItem>
              <MenuItem value={30}>30 days</MenuItem>
              <MenuItem value={90}>90 days</MenuItem>
            </Select>
          </FormControl>
          <Tooltip title={t('admin.export', 'Export to CSV')}>
            <IconButton onClick={handleExport}>
              <DownloadIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title={t('common.refresh', 'Refresh')}>
            <IconButton onClick={() => window.location.reload()}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Stack>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {loading && <LinearProgress sx={{ mb: 2 }} />}

      {summary && (
        <>
          {/* Summary Cards */}
          <Grid container spacing={3} mb={3}>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title={t('admin.totalCost', 'Total Cost')}
                value={formatCurrency(summary.total_cost, summary.currency)}
                subtitle={`${summary.call_count} calls`}
                icon={<MoneyIcon />}
                color="primary.main"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title={t('admin.totalTokens', 'Total Tokens')}
                value={formatNumber(summary.total_tokens)}
                subtitle={`${formatNumber(summary.total_input_tokens)} in / ${formatNumber(summary.total_output_tokens)} out`}
                icon={<TokenIcon />}
                color="secondary.main"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title={t('admin.avgCostPerCall', 'Avg Cost/Call')}
                value={formatCurrency(summary.avg_cost_per_call, summary.currency)}
                icon={<SpeedIcon />}
                color="info.main"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title={t('admin.avgTokensPerCall', 'Avg Tokens/Call')}
                value={formatNumber(summary.avg_tokens_per_call)}
                icon={<TokenIcon />}
                color="warning.main"
              />
            </Grid>
          </Grid>

          {/* Tabs */}
          <Paper elevation={0} sx={{ mb: 3 }}>
            <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)}>
              <Tab label={t('admin.overview', 'Overview')} />
              <Tab label={t('admin.byModel', 'By Model')} />
              <Tab label={t('admin.records', 'Records')} />
            </Tabs>
          </Paper>

          {/* Overview Tab */}
          {tabValue === 0 && (
            <Grid container spacing={3}>
              {/* Daily Cost Chart */}
              <Grid item xs={12} lg={8}>
                <Paper elevation={0} sx={{ p: 3 }}>
                  <Typography variant="h6" mb={2}>
                    {t('admin.dailyCost', 'Daily Cost Trend')}
                  </Typography>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={dailyData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis />
                      <ChartTooltip
                        formatter={(value: number) => [formatCurrency(value), 'Cost']}
                      />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="cost"
                        stroke="#8884d8"
                        strokeWidth={2}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </Paper>
              </Grid>

              {/* Model Distribution Pie */}
              <Grid item xs={12} lg={4}>
                <Paper elevation={0} sx={{ p: 3 }}>
                  <Typography variant="h6" mb={2}>
                    {t('admin.costByModel', 'Cost by Model')}
                  </Typography>
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={modelChartData}
                        dataKey="cost"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        outerRadius={100}
                        label={({ name, percent }) =>
                          `${name} (${(percent * 100).toFixed(0)}%)`
                        }
                      >
                        {modelChartData.map((_, index) => (
                          <Cell key={index} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <ChartTooltip
                        formatter={(value: number) => formatCurrency(value)}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </Paper>
              </Grid>

              {/* Top Users */}
              <Grid item xs={12}>
                <Paper elevation={0} sx={{ p: 3 }}>
                  <Typography variant="h6" mb={2}>
                    {t('admin.topUsers', 'Top Users by Cost')}
                  </Typography>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={userChartData} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" />
                      <YAxis type="category" dataKey="name" width={150} />
                      <ChartTooltip
                        formatter={(value: number) => formatCurrency(value)}
                      />
                      <Bar dataKey="cost" fill="#8884d8" />
                    </BarChart>
                  </ResponsiveContainer>
                </Paper>
              </Grid>
            </Grid>
          )}

          {/* By Model Tab */}
          {tabValue === 1 && (
            <Paper elevation={0}>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>{t('admin.model', 'Model')}</TableCell>
                      <TableCell align="right">{t('admin.calls', 'Calls')}</TableCell>
                      <TableCell align="right">{t('admin.tokens', 'Tokens')}</TableCell>
                      <TableCell align="right">{t('admin.cost', 'Cost')}</TableCell>
                      <TableCell align="right">{t('admin.avgCost', 'Avg Cost')}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {modelChartData.map((row) => (
                      <TableRow key={row.name}>
                        <TableCell>
                          <Chip label={row.name} size="small" />
                        </TableCell>
                        <TableCell align="right">{formatNumber(row.calls)}</TableCell>
                        <TableCell align="right">{formatNumber(row.tokens)}</TableCell>
                        <TableCell align="right">
                          {formatCurrency(row.cost, summary.currency)}
                        </TableCell>
                        <TableCell align="right">
                          {formatCurrency(row.cost / row.calls, summary.currency)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          )}

          {/* Records Tab */}
          {tabValue === 2 && (
            <Paper elevation={0}>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>{t('admin.timestamp', 'Timestamp')}</TableCell>
                      <TableCell>{t('admin.user', 'User')}</TableCell>
                      <TableCell>{t('admin.model', 'Model')}</TableCell>
                      <TableCell align="right">{t('admin.inputTokens', 'Input')}</TableCell>
                      <TableCell align="right">{t('admin.outputTokens', 'Output')}</TableCell>
                      <TableCell align="right">{t('admin.cost', 'Cost')}</TableCell>
                      <TableCell align="right">{t('admin.duration', 'Duration')}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {records.map((record) => (
                      <TableRow key={record.id}>
                        <TableCell>
                          {new Date(record.timestamp).toLocaleString()}
                        </TableCell>
                        <TableCell>{record.user_id}</TableCell>
                        <TableCell>
                          <Chip label={record.model} size="small" />
                        </TableCell>
                        <TableCell align="right">
                          {formatNumber(record.input_tokens)}
                        </TableCell>
                        <TableCell align="right">
                          {formatNumber(record.output_tokens)}
                        </TableCell>
                        <TableCell align="right">
                          {formatCurrency(record.cost)}
                        </TableCell>
                        <TableCell align="right">
                          {(record.execution_time_ms / 1000).toFixed(2)}s
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
              <TablePagination
                component="div"
                count={recordsTotal}
                page={page}
                onPageChange={(_, p) => setPage(p)}
                rowsPerPage={pageSize}
                onRowsPerPageChange={(e) => {
                  setPageSize(parseInt(e.target.value, 10));
                  setPage(0);
                }}
                rowsPerPageOptions={[10, 25, 50, 100]}
              />
            </Paper>
          )}
        </>
      )}
    </Box>
  );
};

export default CostReportPage;
