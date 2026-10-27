import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

type BacktestPoint={observation:number;strategy:number;benchmark:number|undefined}

export default function BacktestChart({points}:{points:BacktestPoint[]}){
  return <div className="chart-frame" role="img" aria-label="Backtest strategy and benchmark equity curves">
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={points} margin={{top:8,right:10,left:4,bottom:4}}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2b392e"/>
        <XAxis dataKey="observation" tick={{fill:'#8b998d',fontSize:9}} tickLine={false} axisLine={{stroke:'#3b4b3d'}}/>
        <YAxis width={66} tick={{fill:'#8b998d',fontSize:9}} tickLine={false} axisLine={false} tickFormatter={(value:number)=>Number(value).toLocaleString(undefined,{maximumFractionDigits:0})}/>
        <Tooltip contentStyle={{background:'#141b16',border:'1px solid #3b4b3d',borderRadius:7,color:'#e8eee8',fontSize:10}} labelStyle={{color:'#a0ada1'}} formatter={value=>Number(value).toLocaleString(undefined,{maximumFractionDigits:2})}/>
        <Legend wrapperStyle={{fontSize:10,color:'#a0ada1'}}/>
        <Line type="monotone" dataKey="strategy" name="Strategy" stroke="#d8fa6a" strokeWidth={2} dot={false} isAnimationActive={false}/>
        <Line type="monotone" dataKey="benchmark" name="Buy-and-hold benchmark" stroke="#82b5a0" strokeWidth={1.5} dot={false} isAnimationActive={false}/>
      </LineChart>
    </ResponsiveContainer>
  </div>
}
