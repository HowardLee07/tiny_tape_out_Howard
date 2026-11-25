// SPDX-License-Identifier: Apache-2.0
`default_nettype none

module tt_um_howardlee_logic_analyzer_4ch (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);
    logic_analyzer_4ch u_analyzer (
        .clk              (clk),
        .rst_n            (rst_n),
        .arm              (ui_in[4]),
        .channels         (ui_in[3:0]),
        .trigger_mask     (uio_in[7:4]),
        .trigger_value    (uio_in[3:0]),
        .rd_addr          ({uio_in[1:0], ui_in[7:5]}),
        .rd_data          (uo_out[3:0]),
        .done             (uo_out[4]),
        .ready_to_trigger (uo_out[5])
    );

    assign uo_out[7:6] = 2'b0;
    assign uio_out     = 8'b0;
    assign uio_oe      = 8'b0;

    wire _unused = &{ena, 1'b0};
endmodule

`default_nettype wire
