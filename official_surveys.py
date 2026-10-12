"""Direct public Michigan survey actuals. No assumed consensus or publication time."""
import math
import re
import urllib.request
from datetime import datetime,timezone
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

SOURCE='https://www.sca.isr.umich.edu/'


class FrontTable(HTMLParser):
    def __init__(self):
        super().__init__();self.active=False;self.rows=[];self.row=None;self.cell=None;self.text=[]
    def handle_starttag(self,tag,attrs):
        if tag=='table' and dict(attrs).get('id')=='front_table':self.active=True
        if self.active and tag=='tr':self.row=[]
        if self.active and tag in ('td','th'):self.cell=[]
    def handle_data(self,data):
        self.text.append(data)
        if self.active and self.cell is not None:self.cell.append(data)
    def handle_endtag(self,tag):
        if self.active and tag in ('td','th') and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split()));self.cell=None
        if self.active and tag=='tr' and self.row is not None:
            self.rows.append(self.row);self.row=None
        if tag=='table':self.active=False


def parse(html,now):
    p=FrontTable();p.feed(html);text=' '.join(' '.join(p.text).split())
    header=re.search(r'\b(Preliminary|Final) Results for ([A-Za-z]+) (\d{4})\b',text)
    if not header:raise ValueError('report_period_missing')
    stage,month,year=header.groups()
    period=datetime.strptime(month+' '+year,'%B %Y').date()
    if period.replace(day=1)>now.date().replace(day=1):raise ValueError('future_report_period')
    if (now.year-period.year)*12+now.month-period.month>2:raise ValueError('report_period_stale')
    rows=p.rows
    prior_month=12 if period.month==1 else period.month-1
    prior_year=period.year-1 if period.month==1 else period.year
    if (len(rows)!=5 or len(rows[0])<3 or len(rows[1])<3
        or rows[0][1]!=period.strftime('%b')
        or rows[0][2]!=datetime(prior_year,prior_month,1).strftime('%b')
        or rows[1][1]!=str(period.year) or rows[1][2]!=str(prior_year)):
        raise ValueError('actual_previous_columns_unverified')
    expected={'Index of Consumer Sentiment':'sentiment',
              'Current Economic Conditions':'current_conditions',
              'Index of Consumer Expectations':'expectations'}
    values={}
    for row in rows[2:]:
        if len(row)<3 or row[0] not in expected:raise ValueError('indicator_identity_unverified')
        actual,previous=float(row[1]),float(row[2])
        if not all(math.isfinite(v) and 0<=v<=200 for v in (actual,previous)):
            raise ValueError('indicator_value_invalid')
        values[expected[row[0]]]={'actual':actual,'previous':previous}
    if len(values)!=3:raise ValueError('indicator_duplicate_or_missing')
    return {'source':SOURCE,'report_stage':stage,'report_period':period.isoformat(),
            'checked_utc':now.isoformat(),'official_values':values,
            'publication_utc':None,'market_consensus':None,
            'current_release_confirmation':False}


def fetch(now):
    req=urllib.request.Request(SOURCE,headers={'User-Agent':'PersonalGoldMonitor/1.0'})
    with urllib.request.urlopen(req,timeout=10) as response:
        html=response.read(200000).decode('utf-8')
    return parse(html,datetime.now(timezone.utc))


def context(now,event_window=False):
    if now.minute>=5 and not event_window:
        return 'Official Michigan source not refreshed this check; last publication/consensus not assumed.'
    try:
        result=fetch(now);v=result['official_values']['sentiment']
        check=datetime.fromisoformat(result['checked_utc']).astimezone(ZoneInfo('Asia/Kolkata')).strftime('%H:%M IST')
        return (f"Official Michigan {result['report_stage']} {result['report_period'][:7]}: "
                f"sentiment {v['actual']:g}, previous {v['previous']:g}; source checked {check}. "
                'Release publication time and market consensus unverified; no current news-direction confirmation. '+SOURCE)
    except Exception:
        return 'Official Michigan source unavailable/invalid this check; actual verification incomplete.'