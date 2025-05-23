"""
Copyright 2019 Goldman Sachs.
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""
import datetime as dt
from typing import Iterable, Optional, Tuple, Union, Type

from gs_quant.base import InstrumentBase, RiskKey
from gs_quant.common import RiskMeasure
from gs_quant.datetime.date import date_range
from gs_quant.risk import RollFwd, MarketDataScenario
from gs_quant.risk.results import HistoricalPricingFuture, PricingFuture
from .core import PricingContext
from .markets import CloseMarket
from ..api.risk import GenericRiskApi


class HistoricalPricingContext(PricingContext):
    """
    A context for producing valuations over multiple dates
    """

    def __init__(
            self,
            start: Optional[Union[int, dt.date]] = None,
            end: Optional[Union[int, dt.date]] = None,
            calendars: Union[str, Tuple] = (),
            dates: Optional[Iterable[dt.date]] = None,
            is_async: bool = None,
            is_batch: bool = None,
            use_cache: bool = None,
            visible_to_gs: bool = None,
            request_priority: Optional[int] = None,
            csa_term: str = None,
            market_data_location: Optional[str] = None,
            timeout: Optional[int] = None,
            show_progress: Optional[bool] = None,
            use_server_cache: Optional[bool] = None,
            provider: Optional[Type[GenericRiskApi]] = None):
        """
        A context for producing valuations over multiple dates

        :param start: start date
        :param end: end date (defaults to today)
        :param calendars: holiday calendars
        :param dates: a custom iterable of dates
        :param is_async: return immediately (True) or wait for results (False) (defaults to False)
        :param is_batch: use for calculations expected to run longer than 3 mins, to avoid timeouts.
            It can be used with is_async=True|False (defaults to False)
        :param use_cache: store results in the pricing cache (defaults to False)
        :param visible_to_gs: are the contents of risk requests visible to GS (defaults to False)
        :param csa_term: the csa under which the calculations are made. Default is local ccy ois index
        :param market_data_location: the location for sourcing market data ('NYC', 'LDN' or 'HKG' (defaults to LDN)
        :param timeout: the timeout for batch operations
        :param show_progress: add a progress bar (tqdm)
        :param use_server_cache: cache query results on the GS servers

        **Examples**

        >>> from gs_quant.instrument import IRSwap
        >>>
        >>> ir_swap = IRSwap('Pay', '10y', 'DKK')
        >>> with HistoricalPricingContext(10):
        >>>     price_f = ir_swap.price()
        >>>
        >>> price_series = price_f.result()
        """
        super().__init__(is_async=is_async, is_batch=is_batch, use_cache=use_cache, visible_to_gs=visible_to_gs,
                         request_priority=request_priority, csa_term=csa_term,
                         market_data_location=market_data_location, timeout=timeout, show_progress=show_progress,
                         use_server_cache=use_server_cache, use_historical_diddles_only=True, provider=provider)

        if start is not None:
            if dates is not None:
                raise ValueError('Must supply start or dates, not both')

            if end is None:
                end = dt.date.today()

            self.__date_range = tuple(date_range(start, end, calendars=calendars))
        elif dates is not None:
            self.__date_range = tuple(dates)
        else:
            raise ValueError('Must supply start or dates')

    def _market(self, date: dt.date, location: str) -> CloseMarket:
        return CloseMarket(location=location, date=date, check=True)

    def calc(self, instrument: InstrumentBase, risk_measure: RiskMeasure) -> PricingFuture:
        futures = []

        provider = instrument.provider if self.provider is None else self.provider
        scenario = self._scenario
        parameters = self._parameters
        location = self.market.location

        for date in self.__date_range:
            risk_key = RiskKey(provider, date, self._market(date, location), parameters, scenario, risk_measure)
            futures.append(self._calc(instrument, risk_key))

        return HistoricalPricingFuture(futures)

    @property
    def date_range(self):
        return self.__date_range


class BackToTheFuturePricingContext(HistoricalPricingContext):
    """
    A context for producing valuations over multiple dates both in the past and into the future
    """

    def __init__(
            self,
            start: Optional[Union[int, dt.date]] = None,
            end: Optional[Union[int, dt.date]] = None,
            calendars: Union[str, Tuple] = (),
            dates: Optional[Iterable[dt.date]] = None,
            roll_to_fwds: bool = True,
            is_async: bool = None,
            is_batch: bool = None,
            use_cache: bool = None,
            visible_to_gs: bool = None,
            csa_term: str = None,
            market_data_location: Optional[str] = None,
            timeout: Optional[int] = None,
            show_progress: Optional[bool] = None,
            name: Optional[str] = None,
            provider: Optional[Type[GenericRiskApi]] = None):
        """
        A context for producing valuations over multiple dates

        :param start: start date
        :param end: end date (defaults to today)
        :param calendars: holiday calendars
        :param dates: a custom iterable of dates
        :param roll_to_fwds: if True then for future dates assume fwd curve is realised.  If False assume spot rates
            are realised.  (defaults to True)
        :param is_async: return immediately (True) or wait for results (False) (defaults to False)
        :param is_batch: use for calculations expected to run longer than 3 mins, to avoid timeouts.
            It can be used with is_async=True|False (defaults to False)
        :param use_cache: store results in the pricing cache (defaults to False)
        :param visible_to_gs: are the contents of risk requests visible to GS (defaults to False)
        :param csa_term: the csa under which the calculations are made. Default is local ccy ois index
        :param market_data_location: the location for sourcing market data ('NYC', 'LDN' or 'HKG' (defaults to LDN)

        **Examples** assuming today is between dt.date(2020, 7, 6) and dt.date(2020, 7, 14)

        >>> from gs_quant.instrument import IRSwap
        >>>
        >>> ir_swap = IRSwap('Pay', '10y', 'DKK')
        >>> with BackToTheFuturePricingContext(dt.date(2020, 7, 6), dt.date(2020, 7, 14), roll_to_fwds=True):
        >>>     price_f = ir_swap.price()
        >>>
        >>> price_series = price_f.result()
        """
        super().__init__(start=start, end=end, calendars=calendars, dates=dates,
                         is_async=is_async, is_batch=is_batch, use_cache=use_cache, visible_to_gs=visible_to_gs,
                         csa_term=csa_term, market_data_location=market_data_location,
                         timeout=timeout, show_progress=show_progress, provider=provider)
        self._roll_to_fwds = roll_to_fwds
        self.name = name
        if start is not None:
            if dates is not None:
                raise ValueError('Must supply start or dates, not both')

            if end is None:
                end = dt.date.today()

            self.__date_range = tuple(date_range(start, end, calendars=calendars))
        elif dates is not None:
            self.__date_range = tuple(dates)
        else:
            raise ValueError('Must supply start or dates')

    def calc(self, instrument: InstrumentBase, risk_measure: RiskMeasure) -> PricingFuture:
        futures = []

        provider = instrument.provider if self.provider is None else self.provider
        base_scenario = self._scenario
        parameters = self._parameters
        location = self.market.location
        base_market = self.market

        for date in self.__date_range:
            if date > self.pricing_date:
                scenario = MarketDataScenario(RollFwd(date=date, realise_fwd=self._roll_to_fwds, name=self.name))
                risk_key = RiskKey(provider, date, base_market, parameters, scenario, risk_measure)
                futures.append(self._calc(instrument, risk_key))
            else:
                risk_key = RiskKey(provider, date, self._market(date, location), parameters, base_scenario,
                                   risk_measure)
                futures.append(self._calc(instrument, risk_key))

        return HistoricalPricingFuture(futures)
