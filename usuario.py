#!/usr/bin/env python
# coding: utf-8

import pandas as pd
import datetime as dt
import matplotlib.pyplot as plt
from tkinter import Tk, filedialog

root = Tk()
root.withdraw()
titulo = input("Inserir titulo do gráfico: ")
filename = filedialog.askopenfilename()

PRIMEIRO_TURNO = (1, 'primeiro_turno_perc')
SEGUNDO_TURNO = (2, 'segundo_turno_perc')
TERCEIRO_TURNO = (3, 'terceiro_turno_perc')

def definir_skip(file):
    with open(file) as f:
        if "General Cutfile" in f.readline(): sk_row = 1
        else: sk_row = 0
    return sk_row

def subtrai_25_idle(line):
    if line.idle > 2.5:
        return line.idle - 2.5
    return 0 

def contar_intervalos(df):
    return df[df>50].count()

def substitui_virgulas(df):
    for col in ['status','pieces_cut','bites_cut','scale_x','scale_y','ply_count','cut','dry_haul','sharpen','bite','interrupt','processing','idle','dry_run','cut_1','dry_haul_1','dry_run_1','cut_speed','throughput','feed_rate']:
        try:    
            df[col] = df[col].str.replace(",",".")
        except:
            continue

def retorna_turno_idle(line):
    '''
    Turno vai das 6h00 até 15h48
    Depois até 01h09
    Depois 
    '''
    start_time = line.start_time.time()
    idle_time = dt.timedelta(minutes=int(line.idle), seconds=60*(line.idle-int(line.idle)))
        
def retorna_turno(time):
    '''
    6h00 até 15h48
    Depois até 01h09
    '''

    if dt.time(hour=6) <= time.time() < dt.time(hour=15, minute=48):
        return PRIMEIRO_TURNO
    elif dt.time(hour=1, minute=9) < time.time() < dt.time(hour =6):
        return TERCEIRO_TURNO
    else:
        return SEGUNDO_TURNO
    
def retorna_share_e_turnos(line):
    def _calcula_tempo(line, turno):
        #if line.interrupt == 701.017:
        #    set_trace()
        if turno == PRIMEIRO_TURNO:
            tempo = (dt.datetime.combine(line.end_time.date(), dt.time(hour=6)) - line.start_time).total_seconds()
        elif turno == SEGUNDO_TURNO:
            tempo = (dt.datetime.combine(line.end_time.date(), dt.time(hour=15, minute=48)) - line.start_time).total_seconds()
        else:
            tempo = (dt.datetime.combine(line.end_time.date(), dt.time(hour=1, minute=9)) - line.start_time).total_seconds()
        return tempo
    
    turno_start = retorna_turno(line.start_time)
    turno_fim = retorna_turno(line.end_time)
    if turno_start == turno_fim:
        line[turno_start[1]] = 1
    else:
        tempo_start = _calcula_tempo(line, turno_fim)
        tempo_total = line.total_time.total_seconds()
        line[turno_start[1]] = tempo_start/tempo_total
        line[turno_fim[1]] = 1 - tempo_start/tempo_total

    return line

def subtrai_idle(line):
    def _calcula_base(turno, line):
        if turno == PRIMEIRO_TURNO:
            valor = (line.start_time - dt.datetime.combine(line.start_time.date(), dt.time(hour=6))).total_seconds()
        elif turno == SEGUNDO_TURNO:
            valor = (line.start_time - dt.datetime.combine(line.start_time.date(), dt.time(hour=15, minute=48))).total_seconds()
        else:
            valor = (line.start_time - dt.datetime.combine(line.start_time.date(), dt.time(hour=1, minute=9))).total_seconds()
        return valor/60
    turno_start = retorna_turno(line.start_time)
    turno_idle = retorna_turno(line.start_time - dt.timedelta(minutes=line.idle))
    valor = line.idle
    if (valor > 150) or (turno_start != turno_idle):
        valor = _calcula_base(turno_start, line)
        if valor > 120:
            valor = 0
    return valor

def subtrai_interrupt(line):
    def _calcula_base(turno, line):
        valor = line.interrupt
        if turno == PRIMEIRO_TURNO:
            if (line.start_time + dt.timedelta(
                minutes=line.cut+line.dry_haul+line.sharpen+line.bite
            ) > dt.datetime.combine(line.end_time.date(), dt.time(hour=15, minute=48))):
                valor = 0
        elif turno == SEGUNDO_TURNO:
            if (line.start_time + dt.timedelta(
                minutes=line.cut+line.dry_haul+line.sharpen+line.bite
            ) > dt.datetime.combine(line.end_time.date(), dt.time(hour=1, minute=9))):
                valor = 0
        else:
            if (line.start_time + dt.timedelta(
                minutes=line.cut+line.dry_haul+line.sharpen+line.bite
            ) > dt.datetime.combine(line.end_time.date(), dt.time(hour=6))):
                valor = 0
        return valor
    turno_start = retorna_turno(line.start_time)
    turno_interrupt = retorna_turno(line.start_time + dt.timedelta(minutes=line.cut+line.dry_haul+line.sharpen+line.bite+line.interrupt))
    valor = line.interrupt
    if (valor > 150) or (turno_start != turno_interrupt and valor > 120):
        valor = _calcula_base(turno_start, line)
        if valor > 120:
            valor = 0
    return valor

df = pd.read_fwf(filename, skiprows=definir_skip(filename))

df = df.dropna(subset=['Cutfile Name','Status']).reset_index(drop=True)
df.rename(columns={'DryHaul':'dry_haul', 'Intrpt':'interrupt','Proc':'processing'}, inplace=True)

if "___" in df.iloc[0]["Cutfile Name"]:
    df.drop(index=0, inplace=True)
df.columns = df.columns.str.lower().str.replace(' ','_').str.replace('.','_', regex=False).str.strip()
 
for col in ['start_time','end_time']:
    df[col] = pd.to_datetime(df[col], dayfirst=True)
df['total_time'] = pd.to_timedelta(df.total_time)

substitui_virgulas(df)

df = df[['start_time','end_time','total_time','cut','dry_haul','sharpen','bite','interrupt','processing','idle']]
for col in ['cut','dry_haul','sharpen','bite','interrupt','processing','idle']:
    df[col] = pd.to_numeric(df[col])
    
df.to_excel(filename[:-4]+'.xlsx')

df['primeiro_turno_perc'] = 0
df['segundo_turno_perc'] = 0
df['terceiro_turno_perc'] = 0

almocos = df[(df.start_time.dt.hour>=9)&(df.end_time.dt.hour<=14)&(df.start_time.dt.hour!=df.end_time.dt.hour)].set_index('start_time').resample('D')[['interrupt','idle']].max().apply(contar_intervalos)
jantar = df[(df.start_time.dt.hour>=19)&(df.end_time.dt.hour<24)&(df.start_time.dt.hour!=df.end_time.dt.hour)].set_index('start_time').resample('D')[['interrupt','idle']].max().apply(contar_intervalos)

df = df.apply(retorna_share_e_turnos, axis=1)
df.at[1, 'idle'] = 0
df.idle = df.apply(subtrai_25_idle, axis=1)
df.idle = df.apply(subtrai_idle, axis=1)
df.interrupt = df.apply(subtrai_interrupt, axis=1)

tempo_produtivo = [0] * 3
tempo_interrompido = [0] * 3
tempo_processando = [0] * 3
tempo_idle = [0] * 3
for i in range(3):
    tempo_produtivo[i] += (df[['cut','dry_haul','sharpen','bite']].T@df.iloc[:,-3+i]).sum()
    tempo_interrompido[i] += (df[['interrupt']].T@df.iloc[:,-3+i]).sum()
    tempo_processando[i] += (df[['processing']].T@df.iloc[:,-3+i]).sum()
    tempo_idle[i] += (df[['idle']].T@df.iloc[:,-3+i]).sum()
    
df_prod = pd.DataFrame(zip(tempo_produtivo, tempo_interrompido, tempo_processando, tempo_idle), 
             index=["Turno 1","Turno 2","Turno 3"],
            columns=["Tempo de Corte","Interrupção","Preparação","Tempo entre Enfesto"]).T
df_prod.iloc[-1,0] = df_prod.iloc[-1,0] - almocos[1]*60
df_prod.iloc[1,0] = df_prod.iloc[1,0] - almocos[0]*60
df_prod.iloc[-1, 1] = df_prod.iloc[-1, 1] - jantar[1]*60
df_prod.iloc[1, 1] = df_prod.iloc[1, 1] - jantar[0]*60

fig, ax = plt.subplots(1,3,sharey=True,figsize=(20,10),)
import matplotlib
matplotlib.rcParams.update({'font.size': 14})
colors = ["green","blue","yellow","red"]
for i in range(3):
    
    if sum(df_prod[f"Turno {i+1}"]):
        ax[i].set_title(f'Turno {i+1}')
        ax[i].pie(
            df_prod[f'Turno {i+1}'],
            startangle=90,
            radius=1,
            colors=colors,
            shadow=True, autopct="%1.1f%%", 
            pctdistance=1.2,
            labeldistance=0,
            normalize=True,
        )
        ax[i].legend(labels=df_prod.index.tolist(), loc="upper center" ,fancybox=True, bbox_to_anchor=(0.5,0), shadow=True, ncol=2)


fig.suptitle(titulo, fontsize=25)
fig.tight_layout()
plt.savefig(filename[:-4]+'.png')

gerencial = input("Gerencial? (s/n)")
if gerencial == "s":
    plt.clf()
    fig, ax = plt.subplots(1, 1, figsize=(20,10))
    ax.set_title("Relatório Gerencial - Todos os Turnos")
    ax.pie(
	df_prod["gerencial"], startangle=90, radius=1, colors=colors,
	shadow=True, autopct="%1.1f%%", pctdistance=1.2, labeldistance=0, normalize=True
	)
    ax.legend(
        labels=df_prod.index.tolist(), loc="upper center" ,fancybox=True, bbox_to_anchor=(0.5,0), shadow=True, ncol=2
        )
    plt.savefig(filename[:-4]+'_GERENCIAL.png')
    

