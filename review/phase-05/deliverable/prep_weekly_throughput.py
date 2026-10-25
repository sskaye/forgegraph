import sys, pandas as pd
src, out = sys.argv[1], sys.argv[2]
d = pd.read_excel(src, 'Runs', header=3)
d = d[d['Run ID'].astype(str).str.startswith('R-')]          # drop title/footer rows
c = d[d.Status.str.strip().str.title() == 'Completed']       # 'completed', 'Completed ' variants
c = c.assign(Week=c.Finished.dt.to_period('W-SUN').dt.start_time)
t = c.pivot_table(index='Week', columns='Instrument', values='Run ID', aggfunc='count', fill_value=0)
t = t[['HPLC-01', 'HPLC-02', 'GC-MS-01', 'ICP-OES-01']]
long = t.reset_index().melt(id_vars='Week', var_name='Instrument', value_name='Completed runs')
long['Completed runs'] = long['Completed runs'].astype(int)
long.to_parquet(out, index=False)
print(long.groupby('Instrument')['Completed runs'].sum(), len(long))
