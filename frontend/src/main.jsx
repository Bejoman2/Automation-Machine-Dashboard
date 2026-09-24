import React, {useEffect, useMemo, useRef, useState} from "react"
import {createRoot} from "react-dom/client"
import axios from "axios"
import {BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend} from "recharts"
import "./styles.css"

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api"
const api = axios.create({baseURL: API})

function getLocalDate(){
  const d = new Date()
  const offset = d.getTimezoneOffset()
  return new Date(d.getTime() - offset * 60000).toISOString().slice(0,10)
}

function getStoredRefreshRate(){
  try{
    const value = Number(localStorage.getItem("dashboard_refresh_rate"))
    return [0,1,2,5,10,30,60].includes(value) ? value : 5
  }catch{
    return 5
  }
}

function App(){
  const [page,setPage]=useState("dashboard")
  const [shifts,setShifts]=useState([])
  const [stations,setStations]=useState([])
  const [targets,setTargets]=useState([])
  const [sources,setSources]=useState([])
  const [corrections,setCorrections]=useState([])
  const [shiftId,setShiftId]=useState("")
  const [date,setDate]=useState(getLocalDate())
  const [summary,setSummary]=useState(null)
  const [busy,setBusy]=useState(false)
  const [msg,setMsg]=useState("")
  const [refreshRate,setRefreshRate]=useState(getStoredRefreshRate)
  const [liveRefreshing,setLiveRefreshing]=useState(false)
  const liveLock=useRef(false)

  async function loadMasters(){
    const [s,st,t,so,c]=await Promise.all([
      api.get("/shifts"),api.get("/stations"),api.get("/targets"),api.get("/sources"),api.get("/corrections")
    ])
    const sourceRows = await Promise.all(so.data.map(async row => {
      try { const m = await api.get(`/sources/${row.id}/mapping`); return {...row, mapping:m.data} }
      catch { return row }
    }))
    setShifts(s.data); setStations(st.data); setTargets(t.data); setSources(sourceRows); setCorrections(c.data)
    if(!shiftId && s.data.length) setShiftId(String(s.data[0].id))
  }

  async function loadSummary(){
    if(!shiftId || !date){
      setSummary(null)
      return
    }
    try{
      const r=await api.get("/summary/shift",{params:{shift_id:shiftId,date_:date}})
      setSummary(r.data); setMsg("")
    }catch(e){setMsg(e.response?.data?.detail || "Failed to load summary")}
  }

  useEffect(()=>{loadMasters().catch(e=>setMsg(e.message))},[])
  useEffect(()=>{loadSummary()},[shiftId,date])

  useEffect(()=>{
    try{ localStorage.setItem("dashboard_refresh_rate", String(refreshRate)) }catch{}
  },[refreshRate])

  async function refreshLive(){
    if(!shiftId || !date || liveLock.current) return
    liveLock.current=true
    setLiveRefreshing(true)
    try{
      await api.post("/refresh-live", null, {params:{date_:date}})
      await loadSummary()
    }catch(e){
      setMsg(e.response?.data?.detail || e.message)
    }finally{
      liveLock.current=false
      setLiveRefreshing(false)
    }
  }

  useEffect(()=>{
    if(page!=="dashboard" || refreshRate<=0 || !shiftId || !date) return
    refreshLive()
    const timer=setInterval(refreshLive, refreshRate*1000)
    return ()=>clearInterval(timer)
  },[page,refreshRate,shiftId,date])

  async function importCSV(file){
    setBusy(true)
    try{
      const formData = new FormData()
      formData.append("file", file)

      const r = await api.post("/import-csv", formData, {
        headers: {"Content-Type": "multipart/form-data"}
      })

      // Automatically move the dashboard date to the selected CSV's data date.
      // Otherwise a valid imported CSV can appear to show "no change" because
      // the current date filter is pointing at another day.
      if (r.data.min_timestamp) {
        const importedDate = r.data.min_timestamp.slice(0, 10)
        setDate(importedDate)
      }

      setMsg(`${r.data.message} Skipped: ${r.data.skipped}.`)
      await loadMasters()
      // date/shift effect will reload the summary after state update.
      await loadSummary()
    }catch(e){
      setMsg(e.response?.data?.detail || e.message)
    }finally{
      setBusy(false)
    }
  }

  async function refresh(){
    setBusy(true)
    try{
      if(!date){
        setMsg("Select a dashboard date first.")
        return
      }
      const r=await api.post("/refresh-live",null,{params:{date_:date}})
      setMsg(`Live refresh complete: ${r.data.imported} new records from ${r.data.files} CSV files.`)
      await loadSummary()
    }catch(e){setMsg(e.response?.data?.detail || e.message)}
    finally{setBusy(false)}
  }

  return <div className="app">
    <header className="topbar">
      <div className="brand">
        <div className="brand-mark">WIK</div>
        <div><div className="title">AUTOMATION MACHINE</div><div className="subtitle">OUTPUT DASHBOARD / MINI ME 2 LINE</div></div>
      </div>
      <div className="header-actions">
        <span className="status-dot"/> SYSTEM ONLINE
        <label className="refresh-rate">
          LIVE
          <select value={refreshRate} onChange={e=>setRefreshRate(Number(e.target.value))}>
            <option value={0}>OFF</option>
            <option value={1}>1s</option>
            <option value={2}>2s</option>
            <option value={5}>5s</option>
            <option value={10}>10s</option>
            <option value={30}>30s</option>
            <option value={60}>60s</option>
          </select>
        </label>
        <span className="live-status">{refreshRate===0?"MANUAL":liveRefreshing?"UPDATING...":`AUTO ${refreshRate}s`}</span>
        <label className="file-button">
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={async e => {
              const file = e.target.files?.[0]
              if (!file) return
              await importCSV(file)
              e.target.value = ""
            }}
          />
          ▣ SELECT CSV
        </label>
        <button onClick={refresh} disabled={busy}>{busy?"REFRESHING...":"↻ REFRESH FOLDER"}</button>
      </div>
    </header>

    <aside className="sidebar">
      <div className="nav-title">MONITORING</div>
      <Nav label="Dashboard" active={page==="dashboard"} onClick={()=>setPage("dashboard")} icon="▦"/>
      <div className="nav-title">MASTER DATA</div>
      <Nav label="Shift Schedule" active={page==="shifts"} onClick={()=>setPage("shifts")} icon="◷"/>
      <Nav label="Target Output" active={page==="targets"} onClick={()=>setPage("targets")} icon="◎"/>
      <Nav label="Station Master" active={page==="stations"} onClick={()=>setPage("stations")} icon="▤"/>
      <Nav label="CSV Source" active={page==="sources"} onClick={()=>setPage("sources")} icon="▥"/>
      <Nav label="Corrections" active={page==="corrections"} onClick={()=>setPage("corrections")} icon="✎"/>
      <div className="sidebar-footer">V10<br/>CSV → MAPPING → SQLITE → API → REACT</div>
    </aside>

    <main className="content">
      {msg && <div className="message">{msg}</div>}
      {page==="dashboard" && <Dashboard summary={summary} shifts={shifts} shiftId={shiftId} setShiftId={setShiftId} date={date} setDate={setDate} refreshRate={refreshRate}/>}
      {page==="shifts" && <CrudTable title="SHIFT SCHEDULE" rows={shifts} fields={[
        ["name","Name"],["start_time","Start (HH:MM)"],["end_time","End (HH:MM)"],["is_active","Active"]
      ]} endpoint="/shifts" onReload={loadMasters}/>}
      {page==="targets" && <TargetTable rows={targets} shifts={shifts} onReload={loadMasters}/>}
      {page==="stations" && <CrudTable title="STATION MASTER" rows={stations} fields={[
        ["name","Name"],["sequence_order","Sequence"],["is_active","Active"]
      ]} endpoint="/stations" onReload={loadMasters}/>}
      {page==="sources" && <SourceTable rows={sources} stations={stations} onReload={loadMasters}/>}
      {page==="corrections" && <CorrectionTable rows={corrections} onReload={loadMasters}/>}
    </main>
  </div>
}

function Nav({label,active,onClick,icon}){return <button className={"nav "+(active?"active":"")} onClick={onClick}><span>{icon}</span>{label}</button>}

function Dashboard({summary,shifts,shiftId,setShiftId,date,setDate,refreshRate}){
  const achievement = summary?.achievement
  return <section>
    <div className="page-head"><div><div className="eyebrow">PRODUCTION MONITORING</div><h1>Shift Summary</h1></div>
      <div className="filters">
        <span className="live-indicator">{refreshRate===0?"AUTO OFF":`AUTO ${refreshRate}s`}</span>
        <select value={shiftId} onChange={e=>setShiftId(e.target.value)}>{shifts.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select>
        <input type="date" value={date} onChange={e=>setDate(e.target.value)}/>
      </div>
    </div>
    {!summary ? <div className="empty">No summary data.</div> : <>
      <div className="shift-banner"><div><span className="muted">SELECTED SHIFT</span><strong>{summary.shift.name}</strong></div>
      <div><span className="muted">WINDOW</span><strong>{new Date(summary.shift.start).toLocaleString()} → {new Date(summary.shift.end).toLocaleString()}</strong></div></div>
      <div className="cards">
        <Metric label="TOTAL OUTPUT" value={summary.total} unit="PCS" />
        <Metric label="OK OUTPUT" value={summary.ok} unit="PCS" good />
        <Metric label="NG OUTPUT" value={summary.ng} unit="PCS" bad />
        <Metric label="TARGET ACHIEVEMENT" value={achievement==null?"—":achievement.toFixed(1)+"%"} unit={summary.target?`${summary.target} PCS TARGET`:"NO TARGET"} />
      </div>
      <div className="panel">
        <div className="panel-head"><h2>HOURLY OUTPUT</h2><span>{summary.hourly.length} HOUR BUCKETS</span></div>
        <div className="chart"><ResponsiveContainer width="100%" height={340}><BarChart data={summary.hourly}>
          <CartesianGrid strokeDasharray="3 3" stroke="#27302d"/><XAxis dataKey="hour" stroke="#7d8b86"/><YAxis stroke="#7d8b86"/>
          <Tooltip contentStyle={{background:"#111615",border:"1px solid #30403a"}}/><Legend/>
          <Bar dataKey="ok" name="OK" fill="#6ef2a3"/><Bar dataKey="ng" name="NG" fill="#ff6b6b"/>
        </BarChart></ResponsiveContainer></div>
        <table><thead><tr><th>HOUR</th><th>OK</th><th>NG</th><th>TOTAL</th><th>NG RATE</th></tr></thead>
        <tbody>{summary.hourly.map((r,i)=><tr key={i}><td>{r.hour}</td><td className="good">{r.ok}</td><td className="bad">{r.ng}</td><td>{r.total}</td><td>{r.total?(r.ng/r.total*100).toFixed(1):"0.0"}%</td></tr>)}</tbody></table>
      </div>
    </>}
  </section>
}

function Metric({label,value,unit,good,bad}){return <div className="metric"><div className="metric-label">{label}</div><div className={"metric-value "+(good?"good ":"")+(bad?"bad":"")}>{value}</div><div className="metric-unit">{unit}</div></div>}

function CrudTable({title,rows,fields,endpoint,onReload}){
  const empty=Object.fromEntries(fields.map(([k])=>[k,k==="is_active"?true:""]))
  const [form,setForm]=useState(empty)
  const [editing,setEditing]=useState(null)
  async function save(){
    const data={...form}
    if(data.sequence_order!=="") data.sequence_order=Number(data.sequence_order)
    const url=editing?`${endpoint}/${editing}`:endpoint
    await api[editing?"put":"post"](url,data); setEditing(null); setForm(empty); onReload()
  }
  async function del(id){if(confirm("Delete this record?")){await api.delete(`${endpoint}/${id}`);onReload()}}
  return <Master title={title}>
    <div className="form-row">{fields.map(([k,l])=><Field key={k} label={l} type={k==="is_active"?"checkbox":k.includes("time")?"time":k==="sequence_order"?"number":"text"} value={form[k]} onChange={v=>setForm({...form,[k]:v})}/>)}
      <button className="primary" onClick={save}>{editing?"UPDATE":"ADD"}</button></div>
    <Table rows={rows} columns={fields.map(([k,l])=>[k,l])} actions={(r)=><><button className="link" onClick={()=>{setEditing(r.id);setForm({...r})}}>EDIT</button><button className="danger link" onClick={()=>del(r.id)}>DELETE</button></>}/>
  </Master>
}

function TargetTable({rows,shifts,onReload}){
  const [form,setForm]=useState({shift_id:shifts[0]?.id||"",date:getLocalDate(),target_qty:0})
  useEffect(()=>{if(!form.shift_id&&shifts[0])setForm({...form,shift_id:shifts[0].id})},[shifts])
  async function save(){await api.post("/targets",{...form,shift_id:Number(form.shift_id),target_qty:Number(form.target_qty)});onReload()}
  async function del(id){if(confirm("Delete?")){await api.delete(`/targets/${id}`);onReload()}}
  return <Master title="TARGET OUTPUT"><div className="form-row">
    <Field label="SHIFT" type="select" options={shifts.map(s=>({value:s.id,label:s.name}))} value={form.shift_id} onChange={v=>setForm({...form,shift_id:v})}/>
    <Field label="DATE" type="date" value={form.date} onChange={v=>setForm({...form,date:v})}/>
    <Field label="TARGET PCS" type="number" value={form.target_qty} onChange={v=>setForm({...form,target_qty:v})}/>
    <button className="primary" onClick={save}>ADD</button>
  </div>
  <Table rows={rows.map(r=>({...r,shift:shifts.find(s=>s.id===r.shift_id)?.name||r.shift_id}))} columns={[["shift","SHIFT"],["date","DATE"],["target_qty","TARGET PCS"]]} actions={r=><button className="danger link" onClick={()=>del(r.id)}>DELETE</button>}/></Master>
}

async function selectNativeFolder(){
  if(window.electronAPI?.selectFolder){
    return await window.electronAPI.selectFolder()
  }
  // Browser fallback: this can select files from a folder, but cannot expose
  // the real Windows folder path. The native Electron picker is used in the
  // desktop version for persistent folder scanning.
  if(window.showDirectoryPicker){
    try{
      const handle = await window.showDirectoryPicker()
      return {cancelled:false, path:null, name:handle.name, browserOnly:true}
    }catch(e){
      if(e?.name === "AbortError") return {cancelled:true}
      throw e
    }
  }
  return {cancelled:false, unsupported:true}
}

function SourceTable({rows,stations,onReload}){
  const existing=rows[0]
  const [stationId,setStationId]=useState(existing?.station_id || stations[stations.length-1]?.id || "")
  const [path,setPath]=useState(existing?.csv_folder_path || "")
  const [status,setStatus]=useState(null)
  const [busy,setBusy]=useState(false)
  const [headers,setHeaders]=useState([])
  const [sampleRows,setSampleRows]=useState([])
  const [headerFile,setHeaderFile]=useState("")
  const [mapping,setMapping]=useState({timestamp_column:"",output_column:"",crack_column:"",ok_value:"OK"})
  const [mappingLoaded,setMappingLoaded]=useState(false)
  const pollRef=useRef(null)

  useEffect(()=>()=>{if(pollRef.current)clearInterval(pollRef.current)},[])
  useEffect(()=>{
    if(existing){
      setStationId(existing.station_id);setPath(existing.csv_folder_path)
      loadSavedMapping(existing.id)
    }
  },[existing?.id])

  async function loadSavedMapping(sourceId){
    try{
      const r=await api.get(`/sources/${sourceId}/mapping`)
      if(r.data){setMapping(r.data);setMappingLoaded(true)}
    }catch(e){setStatus({status:"error",message:e.response?.data?.detail||e.message})}
  }

  async function detectHeaders(folder=path){
    if(!folder.trim()){setStatus({connected:false,message:"Enter a CSV folder path first."});return false}
    try{
      const r=await api.get("/csv/headers",{params:{folder_path:folder.trim()}})
      setHeaders(r.data.headers||[])
      setSampleRows(r.data.sample_rows||[])
      setHeaderFile(r.data.relative_file||r.data.file||"")
      const recommended=r.data.recommended||{}
      const nextMapping={
        timestamp_column:mapping.timestamp_column||recommended.timestamp_column||r.data.headers?.[0]||"",
        output_column:mapping.output_column||recommended.output_column||r.data.headers?.[0]||"",
        crack_column:mapping.crack_column||recommended.crack_column||"",
        ok_value:mapping.ok_value||recommended.ok_value||"OK"
      }
      setMapping(nextMapping)
      setMappingLoaded(true)
      setStatus({connected:true,message:`Header detected from ${r.data.relative_file||r.data.file||"latest CSV"}.`})
      return {headers:r.data.headers||[],recommended,nextMapping}
    }catch(e){
      setStatus({connected:false,message:e.response?.data?.detail||e.message})
      return false
    }
  }

  async function pollScan(jobId){
    if(pollRef.current)clearInterval(pollRef.current)
    pollRef.current=setInterval(async()=>{
      try{
        const r=await api.get(`/scan-folder/status/${jobId}`);setStatus(r.data)
        if(r.data.status==="completed"||r.data.status==="error"){
          clearInterval(pollRef.current);pollRef.current=null;setBusy(false);await onReload()
        }
      }catch(e){clearInterval(pollRef.current);pollRef.current=null;setBusy(false);setStatus({connected:false,status:"error",message:e.response?.data?.detail||e.message})}
    },500)
  }

  async function startScan(folder){
    const r=await api.post("/scan-folder/start",null,{params:{folder_path:folder}})
    setStatus(r.data)
    if(r.data.job_id)await pollScan(r.data.job_id)
  }

  async function testConnection(){
    if(!path.trim()){setStatus({connected:false,message:"Enter a CSV folder path first."});return}
    setBusy(true)
    try{
      const r=await api.post("/test-folder",null,{params:{folder_path:path.trim()}});setStatus(r.data)
      if(r.data.connected)await detectHeaders(path.trim())
    }catch(e){setStatus({connected:false,message:e.response?.data?.detail||e.message})}
    finally{setBusy(false)}
  }

  async function saveAndScan(){
    if(!path.trim()){setStatus({connected:false,message:"CSV folder path is required."});return}
    setBusy(true)
    try{
      const test=await api.post("/test-folder",null,{params:{folder_path:path.trim()}});setStatus(test.data)
      if(!test.data.connected){setBusy(false);return}
      const detected=await detectHeaders(path.trim())
      if(!detected){setBusy(false);return}
      const activeMapping=detected.nextMapping
      if(!activeMapping.timestamp_column||!activeMapping.output_column){setStatus({connected:false,message:"Select Timestamp and Output Result columns before saving."});setBusy(false);return}
      const payload={station_id:Number(stationId),csv_folder_path:path.trim()}
      let sourceId=existing?.id
      if(sourceId)await api.put(`/sources/${sourceId}`,payload)
      else {const created=await api.post("/sources",payload);sourceId=created.data.id}
      await api.put(`/sources/${sourceId}/mapping`,activeMapping)
      await onReload()
      setMappingLoaded(true)
      await startScan(path.trim())
    }catch(e){setBusy(false);setStatus({connected:false,status:"error",message:e.response?.data?.detail||e.message})}
  }

  async function saveMappingOnly(){
    if(!existing){setStatus({connected:false,message:"Save the CSV source first."});return}
    if(!mapping.timestamp_column||!mapping.output_column){setStatus({connected:false,message:"Timestamp and Output Result columns are required."});return}
    setBusy(true)
    try{
      const r=await api.put(`/sources/${existing.id}/mapping`,mapping)
      setMapping(r.data);setMappingLoaded(true);setStatus({connected:true,message:"CSV column mapping saved."})
    }catch(e){setStatus({connected:false,message:e.response?.data?.detail||e.message})}
    finally{setBusy(false)}
  }

  async function refreshData(){
    if(!path.trim())return
    setBusy(true)
    try{await startScan(path.trim())}
    catch(e){setBusy(false);setStatus({connected:false,status:"error",message:e.response?.data?.detail||e.message})}
  }

  const progress=status?.total?Math.min(100,Math.round(status.current/status.total*100)):0
  const scanning=busy&&(status?.status==="queued"||status?.status==="running")
  const selectOptions=headers.map(h=>({value:h,label:h}))

  return <Master title="CSV SOURCE">
    <div className="source-config">
      <div className="source-config-row">
        <Field label="FINAL STATION" type="select" options={stations.map(s=>({value:s.id,label:s.name}))} value={stationId} onChange={v=>setStationId(v)}/>
        <div className="field folder-field"><span>CSV FOLDER PATH</span><div className="folder-input-row">
          <input value={path} onChange={e=>setPath(e.target.value)} placeholder="Select a Hikrobot CSV folder"/>
          <button className="secondary folder-picker" onClick={async()=>{try{const result=await selectNativeFolder();if(result?.cancelled)return;if(result?.path){setPath(result.path);setStatus({connected:true,folder:result.path,message:"Folder selected. Click TEST CONNECTION."})}else if(result?.browserOnly)setStatus({connected:false,message:"Browser folder picker does not expose the Windows path. Use the Desktop version."})}catch(e){setStatus({connected:false,message:e.message})}}} disabled={busy}>📁 SELECT FOLDER</button>
        </div></div>
      </div>
      <div className="source-actions">
        <button className="secondary" onClick={testConnection} disabled={busy}>TEST CONNECTION + READ HEADER</button>
        <button className="primary" onClick={saveAndScan} disabled={busy}>{scanning?"IMPORTING...":"SAVE MAPPING & SCAN"}</button>
        <button className="secondary" onClick={refreshData} disabled={busy}>REFRESH DATA</button>
      </div>

      {status&&<div className={`source-status ${status.status==="error"||status.connected===false?"error":"ok"}`}>
        <div className="source-status-line"><span className="status-dot"/><strong>{status.status==="running"||status.status==="queued"?"IMPORTING":status.status==="completed"?"IMPORT COMPLETE":status.connected?"CONNECTED":"NOT CONNECTED"}</strong><span>{status.message||""}</span></div>
        {(status.status==="running"||status.status==="queued"||status.status==="completed")&&status.total!=null&&<><div className="progress-track"><div className="progress-fill" style={{width:`${progress}%`}}/></div><div className="progress-meta"><span>{status.current||0} / {status.total||0} CSV files</span><span>{status.imported||0} new records</span></div>{status.file&&<div className="progress-file">Current: {status.file}</div>}</>}
        {status.files_found!=null&&<div className="status-details">Files: {status.files_found} · Date folders: {status.date_folders_found} · Latest: {status.latest_file||"-"}</div>}
      </div>}

      <div className="mapping-panel">
        <div className="panel-head"><h2>CSV HEADER AUTO-DETECT + COLUMN MAPPING</h2><span>{headers.length?`${headers.length} COLUMNS DETECTED`:"WAITING FOR HEADER"}</span></div>
        {headerFile&&<div className="mapping-file">SOURCE FILE: <strong>{headerFile}</strong></div>}
        {!headers.length?<div className="mapping-empty">Click <strong>TEST CONNECTION + READ HEADER</strong> to read the latest CSV header.</div>:<>
          <div className="mapping-grid">
            <Field label="TIMESTAMP COLUMN *" type="select" options={selectOptions} value={mapping.timestamp_column} onChange={v=>setMapping({...mapping,timestamp_column:v})}/>
            <Field label="OUTPUT RESULT COLUMN *" type="select" options={selectOptions} value={mapping.output_column} onChange={v=>setMapping({...mapping,output_column:v})}/>
            <Field label="CRACK / DEFECT COLUMN" type="select" options={[{value:"",label:"— NOT USED —"},...selectOptions]} value={mapping.crack_column} onChange={v=>setMapping({...mapping,crack_column:v})}/>
            <Field label="OK VALUE" value={mapping.ok_value} onChange={v=>setMapping({...mapping,ok_value:v})}/>
          </div>
          <div className="mapping-actions"><button className="primary" onClick={saveMappingOnly} disabled={busy||!existing}>SAVE MAPPING</button><span className="mapping-hint">All other CSV columns are preserved in the source file but are ignored by the MVP importer.</span></div>
          {sampleRows.length>0&&<div className="table-wrap sample-table"><table><thead><tr>{headers.map(h=><th key={h}>{h}</th>)}</tr></thead><tbody>{sampleRows.map((r,i)=><tr key={i}>{headers.map(h=><td key={h}>{String(r[h]??"")}</td>)}</tr>)}</tbody></table></div>}
        </>}
      </div>

      <div className="table-wrap"><table><thead><tr><th>STATION</th><th>CSV FOLDER</th><th>MAPPING</th><th>ACTIONS</th></tr></thead><tbody>
        {rows.map(r=><tr key={r.id}><td>{stations.find(s=>s.id===r.station_id)?.name||r.station_id}</td><td>{r.csv_folder_path}</td><td>{r.mapping?`${r.mapping.timestamp_column} → ${r.mapping.output_column} = ${r.mapping.ok_value}`:"Not configured"}</td><td><button className="secondary" onClick={async()=>{setStationId(r.station_id);setPath(r.csv_folder_path);await loadSavedMapping(r.id);await detectHeaders(r.csv_folder_path)}} disabled={busy}>LOAD</button></td></tr>)}
      </tbody></table></div>
    </div>
  </Master>
}

function CorrectionTable({rows,onReload}){
  const [form,setForm]=useState({production_record_id:"",field_changed:"final_result",new_value:"OK",reason:"",corrected_by:"Engineer"})
  async function save(){await api.post("/corrections",{...form,production_record_id:form.production_record_id?Number(form.production_record_id):null});onReload()}
  return <Master title="MANUAL CORRECTION"><div className="form-row">
    <Field label="RECORD ID" type="number" value={form.production_record_id} onChange={v=>setForm({...form,production_record_id:v})}/>
    <Field label="FIELD" value={form.field_changed} onChange={v=>setForm({...form,field_changed:v})}/>
    <Field label="NEW VALUE" value={form.new_value} onChange={v=>setForm({...form,new_value:v})}/>
    <Field label="REASON" value={form.reason} onChange={v=>setForm({...form,reason:v})}/>
    <Field label="CORRECTED BY" value={form.corrected_by} onChange={v=>setForm({...form,corrected_by:v})}/>
    <button className="primary" onClick={save}>SAVE</button>
  </div><Table rows={rows} columns={[["id","ID"],["production_record_id","RECORD"],["field_changed","FIELD"],["old_value","OLD"],["new_value","NEW"],["reason","REASON"],["corrected_by","BY"],["corrected_at","AT"]]}/></Master>
}

function Master({title,children}){return <section><div className="page-head"><div><div className="eyebrow">MASTER DATA</div><h1>{title}</h1></div></div><div className="panel">{children}</div></section>}

function Field({label,type="text",value,onChange,options=[]}){
  return <label className="field"><span>{label}</span>{type==="checkbox"?<input type="checkbox" checked={!!value} onChange={e=>onChange(e.target.checked)}/>:type==="select"?<select value={value} onChange={e=>onChange(e.target.value)}>{options.map(o=><option key={o.value} value={o.value}>{o.label}</option>)}</select>:<input type={type} value={value??""} onChange={e=>onChange(e.target.value)}/>}</label>
}

function Table({rows,columns,actions}){
  return <div className="table-wrap"><table><thead><tr>{columns.map(c=><th key={c[0]}>{c[1]}</th>)}{actions&&<th>ACTIONS</th>}</tr></thead><tbody>
    {rows.map(r=><tr key={r.id}>{columns.map(c=><td key={c[0]}>{String(r[c[0]]??"")}</td>)}{actions&&<td>{actions(r)}</td>}</tr>)}
  </tbody></table></div>
}

createRoot(document.getElementById("root")).render(<App/>)
