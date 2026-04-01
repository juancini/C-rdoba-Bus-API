"""Unit tests for SQLite proxy classes."""

import pytest

from app.models import StopTime


class TestStopTimesSQLiteProxy:
    """Test the _StopTimesSQLiteProxy class for dict-like interface and queries."""

    def test_get_existing_stop_returns_list_of_stoptimes(self, stop_times_proxy):
        """Test that getting an existing stop returns a list of StopTime objects."""
        arrivals = stop_times_proxy.get("1001")
        assert arrivals is not None
        assert len(arrivals) == 3
        assert all(isinstance(a, StopTime) for a in arrivals)

    def test_get_nonexistent_stop_returns_none(self, stop_times_proxy):
        """Test that getting a non-existent stop returns None."""
        arrivals = stop_times_proxy.get("9999")
        assert arrivals is None

    def test_get_with_default_value(self, stop_times_proxy):
        """Test that get() returns the default value for non-existent stops."""
        arrivals = stop_times_proxy.get("9999", [])
        assert arrivals == []

    def test_arrivals_sorted_by_time(self, stop_times_proxy):
        """Test that arrivals are sorted by arrival_seconds."""
        arrivals = stop_times_proxy.get("1001")
        assert arrivals[0].arrival_seconds == 25200  # 7:00 AM
        assert arrivals[1].arrival_seconds == 28800  # 8:00 AM
        assert arrivals[2].arrival_seconds == 32400  # 9:00 AM

    def test_dict_access_with_getitem(self, stop_times_proxy):
        """Test dict-like access using [] operator."""
        arrivals = stop_times_proxy["1001"]
        assert len(arrivals) == 3

    def test_dict_access_key_error(self, stop_times_proxy):
        """Test that [] raises KeyError for non-existent keys."""
        with pytest.raises(KeyError):
            _ = stop_times_proxy["9999"]

    def test_in_operator_existing_stop(self, stop_times_proxy):
        """Test 'in' operator returns True for existing stops."""
        assert "1001" in stop_times_proxy

    def test_in_operator_nonexistent_stop(self, stop_times_proxy):
        """Test 'in' operator returns False for non-existent stops."""
        assert "9999" not in stop_times_proxy

    def test_stoptime_attributes(self, stop_times_proxy):
        """Test that StopTime objects have correct attributes."""
        arrivals = stop_times_proxy.get("1001")
        st = arrivals[0]
        assert st.trip_id == "T001"
        assert st.route_id == "R100"
        assert st.route_short_name == "10"
        assert st.headsign == "Towards Cerro"
        assert st.arrival_time == "07:00"

    def test_multiple_stops_independent(self, stop_times_proxy):
        """Test that different stops have independent data."""
        arrivals_1001 = stop_times_proxy.get("1001")
        arrivals_1002 = stop_times_proxy.get("1002")

        assert len(arrivals_1001) == 3
        assert len(arrivals_1002) == 2
        assert arrivals_1001[0].trip_id == "T001"
        assert arrivals_1002[0].trip_id == "T002"


class TestTripStopSeqSQLiteProxy:
    """Test the _TripStopSeqSQLiteProxy class for dict-like interface and queries."""

    def test_get_existing_trip_returns_list(self, trip_stop_seq_proxy):
        """Test that getting an existing trip returns a list of stop sequences."""
        seq = trip_stop_seq_proxy.get("T001")
        assert seq is not None
        assert len(seq) == 3
        assert all(isinstance(s, dict) for s in seq)

    def test_get_nonexistent_trip_returns_none(self, trip_stop_seq_proxy):
        """Test that getting a non-existent trip returns None."""
        seq = trip_stop_seq_proxy.get("T999")
        assert seq is None

    def test_get_with_default_value(self, trip_stop_seq_proxy):
        """Test that get() returns the default value for non-existent trips."""
        seq = trip_stop_seq_proxy.get("T999", [])
        assert seq == []

    def test_stops_in_sequence_order(self, trip_stop_seq_proxy):
        """Test that stops are returned in order of stop_sequence."""
        seq = trip_stop_seq_proxy.get("T001")
        assert seq[0]["stop_id"] == "1001"
        assert seq[0]["stop_sequence"] == 1
        assert seq[1]["stop_id"] == "1002"
        assert seq[1]["stop_sequence"] == 2
        assert seq[2]["stop_id"] == "1003"
        assert seq[2]["stop_sequence"] == 3

    def test_dict_access_with_getitem(self, trip_stop_seq_proxy):
        """Test dict-like access using [] operator."""
        seq = trip_stop_seq_proxy["T001"]
        assert len(seq) == 3

    def test_dict_access_key_error(self, trip_stop_seq_proxy):
        """Test that [] raises KeyError for non-existent keys."""
        with pytest.raises(KeyError):
            _ = trip_stop_seq_proxy["T999"]

    def test_in_operator_existing_trip(self, trip_stop_seq_proxy):
        """Test 'in' operator returns True for existing trips."""
        assert "T001" in trip_stop_seq_proxy

    def test_in_operator_nonexistent_trip(self, trip_stop_seq_proxy):
        """Test 'in' operator returns False for non-existent trips."""
        assert "T999" not in trip_stop_seq_proxy

    def test_different_trips_different_orders(self, trip_stop_seq_proxy):
        """Test that different trips have different stop sequences."""
        seq_t001 = trip_stop_seq_proxy.get("T001")
        seq_t002 = trip_stop_seq_proxy.get("T002")

        # T001: 1001 -> 1002 -> 1003
        assert [s["stop_id"] for s in seq_t001] == ["1001", "1002", "1003"]

        # T002: 1003 -> 1002 -> 1001
        assert [s["stop_id"] for s in seq_t002] == ["1003", "1002", "1001"]

    def test_multiple_trips_independent(self, trip_stop_seq_proxy):
        """Test that different trips have independent sequences."""
        seq_t001 = trip_stop_seq_proxy.get("T001")
        seq_t003 = trip_stop_seq_proxy.get("T003")

        assert len(seq_t001) == 3
        assert len(seq_t003) == 2
