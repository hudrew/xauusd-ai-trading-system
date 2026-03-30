//+------------------------------------------------------------------+
//|                                                ExportHistoryCsv  |
//| Purpose: export MT5 bars to CSV for research/backtest reuse.     |
//+------------------------------------------------------------------+
#property script_show_inputs

input string InpSymbol = "XAUUSD";
input ENUM_TIMEFRAMES InpTimeframe = PERIOD_M1;
input int InpBars = 120000;
input string InpOutputFile = "xauusd_m1_history_mt5.csv";
input bool InpUseCommonFolder = true;

string TimeframeLabel(const ENUM_TIMEFRAMES timeframe)
{
   switch(timeframe)
   {
      case PERIOD_M1: return "M1";
      case PERIOD_M5: return "M5";
      case PERIOD_M15: return "M15";
      case PERIOD_M30: return "M30";
      case PERIOD_H1: return "H1";
      case PERIOD_H4: return "H4";
      case PERIOD_D1: return "D1";
      default: return IntegerToString((int)timeframe);
   }
}

void OnStart()
{
   if(!SymbolSelect(InpSymbol, true))
   {
      PrintFormat("EXPORT_FAILED symbol_select symbol=%s", InpSymbol);
      return;
   }

   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   const int copied = CopyRates(InpSymbol, InpTimeframe, 0, InpBars, rates);
   if(copied <= 0)
   {
      PrintFormat(
         "EXPORT_FAILED copy_rates symbol=%s timeframe=%s bars=%d err=%d",
         InpSymbol,
         TimeframeLabel(InpTimeframe),
         InpBars,
         GetLastError()
      );
      return;
   }

   const double point = SymbolInfoDouble(InpSymbol, SYMBOL_POINT);
   const int file_flags = FILE_WRITE | FILE_CSV | FILE_ANSI |
                          (InpUseCommonFolder ? FILE_COMMON : 0);
   const int handle = FileOpen(InpOutputFile, file_flags);
   if(handle == INVALID_HANDLE)
   {
      PrintFormat(
         "EXPORT_FAILED file_open file=%s common=%s err=%d",
         InpOutputFile,
         (InpUseCommonFolder ? "true" : "false"),
         GetLastError()
      );
      return;
   }

   FileWrite(
      handle,
      "timestamp",
      "symbol",
      "open",
      "high",
      "low",
      "close",
      "bid",
      "ask",
      "spread",
      "volume",
      "tick_volume",
      "real_volume"
   );

   for(int i = copied - 1; i >= 0; --i)
   {
      const MqlRates rate = rates[i];
      const double spread = (point > 0.0 ? rate.spread * point : (double)rate.spread);
      const double bid = rate.close - spread / 2.0;
      const double ask = rate.close + spread / 2.0;

      FileWrite(
         handle,
         TimeToString(rate.time, TIME_DATE | TIME_MINUTES),
         InpSymbol,
         DoubleToString(rate.open, _Digits),
         DoubleToString(rate.high, _Digits),
         DoubleToString(rate.low, _Digits),
         DoubleToString(rate.close, _Digits),
         DoubleToString(bid, _Digits),
         DoubleToString(ask, _Digits),
         DoubleToString(spread, _Digits),
         (double)rate.tick_volume,
         (long)rate.tick_volume,
         (long)rate.real_volume
      );
   }

   FileClose(handle);
   PrintFormat(
      "EXPORT_OK symbol=%s timeframe=%s bars=%d file=%s common=%s",
      InpSymbol,
      TimeframeLabel(InpTimeframe),
      copied,
      InpOutputFile,
      (InpUseCommonFolder ? "true" : "false")
   );
}
